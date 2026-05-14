import json
import logging
from datetime import date, datetime, timezone

import dashscope
from dashscope import Generation

from app.agents.trip_planner_agent import generate_itinerary, _extract_json
from app.config import settings
from app.models.schemas import TripRequest
from app.services import map_service, storage_service, weather_service

logger = logging.getLogger(__name__)


async def generate_full_trip(request: TripRequest) -> dict:
    """Generate a complete trip itinerary and enrich with map and weather data."""
    logger.info("Generating trip for %s", request.destination)
    result = generate_itinerary(request)
    days = result.get("days", [])
    logger.info("Trip generated: %s, %d days", result.get("destination"), len(days))

    await _enrich_with_map_data(days, request.destination)
    await _enrich_with_weather(days, request.destination, request.start_date, request.end_date)
    return result


async def _enrich_with_map_data(days: list, destination: str) -> None:
    """Enrich each spot with coordinates/address and add route estimates."""
    for day in days:
        spots = day.get("spots", [])
        if not spots:
            continue

        enriched_spots = []
        for spot in spots:
            name = spot.get("name", "")
            poi = await map_service.search_poi(name, destination)
            if poi:
                spot["address"] = poi["address"]
                spot["location"] = poi["location"]
                spot["poi_id"] = poi.get("poi_id")
                logger.info("Enriched spot '%s': address=%s, location=%s", name, poi["address"], poi["location"])
            else:
                lnglat = await map_service.geocode(f"{destination}{name}")
                if lnglat:
                    spot["location"] = {"lng": lnglat[0], "lat": lnglat[1]}
                    logger.info("Geocode fallback for spot '%s': (%.6f, %.6f)", name, lnglat[0], lnglat[1])
                else:
                    logger.warning("No map data for spot '%s'", name)
            enriched_spots.append(spot)

        day["spots"] = enriched_spots

        spots_with_coords = [
            s for s in enriched_spots
            if s.get("location") and s["location"].get("lng") and s["location"].get("lat")
        ]
        if len(spots_with_coords) >= 2:
            origin = (spots_with_coords[0]["location"]["lng"], spots_with_coords[0]["location"]["lat"])
            dest = (spots_with_coords[-1]["location"]["lng"], spots_with_coords[-1]["location"]["lat"])
            route = await map_service.route_driving(origin, dest)
            if route:
                day["route_estimate"] = route
                logger.info(
                    "Route for day %d: %.1f km, %d min",
                    day.get("day_index"), route["distance_km"], route["duration_min"],
                )


async def _enrich_with_weather(
    days: list, destination: str, start_date: date, end_date: date
) -> None:
    """Fetch weather forecast and match to each day by date."""
    try:
        forecasts = await weather_service.get_forecast(destination, start_date, end_date)
        if not forecasts:
            logger.warning("No weather data available for %s", destination)
            return
        # Build lookup map by date string
        weather_map = {}
        for w in forecasts:
            key = w.date.isoformat() if isinstance(w.date, date) else str(w.date)
            weather_map[key] = w.model_dump(mode="json")

        for day in days:
            day_date = day.get("date", "")
            # Normalize date format
            if isinstance(day_date, str):
                pass  # already string
            elif isinstance(day_date, date):
                day_date = day_date.isoformat()
            if day_date in weather_map:
                day["weather"] = weather_map[day_date]
                logger.info("Weather matched for day %s: %s", day_date, weather_map[day_date].get("condition"))
            else:
                logger.info("No weather match for day %s", day_date)
    except Exception as e:
        logger.warning("Weather enrichment failed for %s: %s", destination, e)


EDIT_SYSTEM_PROMPT = """你是一个旅行行程编辑助手。用户会给你当前某一天的行程JSON，以及修改指令。
请根据修改指令调整当天的行程，然后只输出修改后的当天JSON（与其他天无关）。

输出格式必须与原JSON结构完全一致：
{
  "day_index": 0,
  "date": "YYYY-MM-DD",
  "weather": null,
  "spots": [
    {
      "name": "景点名称",
      "address": "",
      "location": null,
      "visit_duration": "2小时",
      "description": "简要描述",
      "image_url": null,
      "poi_id": null
    }
  ],
  "meals": [
    {"type": "breakfast", "name": "早餐", "description": ""},
    {"type": "lunch", "name": "午餐", "description": ""},
    {"type": "dinner", "name": "晚餐", "description": ""}
  ],
  "hotel": null
}

规则：
1. 只输出JSON，不要任何额外文字
2. 只修改与指令相关的部分，其余保持不变
3. 如果指令要求增加景点，插入到合理位置（考虑游览顺序）
4. 新增景点的 address、location、image_url、poi_id 统一设为空字符串或null
5. 删除景点时从数组中移除对应元素
6. 修改餐食时只改对应type的name和description"""


async def edit_day(trip_id: str, day_index: int, edit_instruction: str) -> dict:
    """Edit a single day in a saved trip using LLM, then re-enrich map data."""
    # Load trip
    trip = storage_service.get_by_id(trip_id)
    if trip is None:
        raise ValueError(f"行程不存在: {trip_id}")

    days = trip.get("days", [])
    if day_index < 0 or day_index >= len(days):
        raise ValueError(f"day_index {day_index} 超出范围 (0~{len(days)-1})")

    original_day = days[day_index]
    destination = trip.get("destination", "")

    # Build edit prompt
    day_json = json.dumps(original_day, ensure_ascii=False, indent=2)
    user_prompt = (
        f"当前第{day_index + 1}天的行程：\n\n{day_json}\n\n"
        f"修改指令：{edit_instruction}\n\n"
        f"请输出修改后的完整当天JSON。"
    )

    # Call LLM
    dashscope.api_key = settings.DASHSCOPE_API_KEY
    messages = [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    new_day = None
    for attempt in range(1, 4):
        try:
            logger.info("Edit LLM attempt %d/3 for trip=%s day=%d", attempt, trip_id, day_index)
            resp = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
            )
            if resp.status_code != 200:
                raise RuntimeError(f"DashScope API error: {resp.status_code}, message={resp.message}")

            content = resp.output.choices[0].message.content
            new_day = _extract_json(content)
            # Preserve original day_index, date, weather
            new_day["day_index"] = original_day.get("day_index", day_index)
            new_day["date"] = original_day.get("date", new_day.get("date", ""))
            new_day["weather"] = original_day.get("weather")
            logger.info("Edit LLM succeeded on attempt %d", attempt)
            break
        except Exception as e:
            last_error = e
            logger.warning("Edit LLM attempt %d failed: %s", attempt, e)
            if attempt >= 3:
                raise RuntimeError(f"行程编辑失败，已重试3次: {last_error}")

    if new_day is None:
        raise RuntimeError(f"行程编辑失败: {last_error}")

    # Replace the day in itinerary
    days[day_index] = new_day
    trip["days"] = days

    # Re-enrich map data for the modified day
    await _enrich_with_map_data([new_day], destination)

    # Update the existing trip in DB
    _update_itinerary_in_db(trip_id, trip)

    logger.info("Day %d edited successfully for trip %s", day_index, trip_id)
    return trip


def _update_itinerary_in_db(trip_id: str, itinerary: dict) -> None:
    """Update the itinerary_json and total_budget for an existing trip."""
    import json as _json
    from app.database import get_session
    from app.models.db_models import TripRecord

    session = get_session()
    try:
        record = session.get(TripRecord, trip_id)
        if record:
            record.itinerary_json = _json.dumps(itinerary, ensure_ascii=False)
            budget = itinerary.get("budget", {})
            record.total_budget = float(budget.get("total", 0)) if isinstance(budget, dict) else 0.0
            record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.commit()
            logger.info("Updated trip %s in DB", trip_id)
    except Exception as e:
        session.rollback()
        logger.error("Failed to update trip %s in DB: %s", trip_id, e)
        raise
    finally:
        session.close()
