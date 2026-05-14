import logging
from datetime import date, datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.schemas import WeatherInfo
from app.services import cache_service

logger = logging.getLogger(__name__)

AMAP_BASE = "https://restapi.amap.com/v3"
WEATHER_TTL = 7200  # 2 hours


async def get_forecast(
    city: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[WeatherInfo]:
    """Get weather forecast for a city. Optionally filter by date range."""
    cache_key = f"weather:{city}"
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("从缓存读取天气: %s", city)
        forecasts = [WeatherInfo(**item) for item in cached]
    else:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{AMAP_BASE}/weather/weatherInfo",
                    params={
                        "key": settings.AMAP_API_KEY,
                        "city": city,
                        "extensions": "all",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                forecasts_data = data.get("forecasts", [])
                if not forecasts_data:
                    logger.warning("天气查询无结果: %s", city)
                    return []
                casts = forecasts_data[0].get("casts", [])
                forecasts = []
                for cast in casts:
                    forecasts.append(WeatherInfo(
                        date=datetime.strptime(cast["date"], "%Y-%m-%d").date(),
                        condition=cast.get("dayweather", ""),
                        temp_high=float(cast.get("daytemp", 0)),
                        temp_low=float(cast.get("nighttemp", 0)),
                        wind=f"{cast.get('daywind', '')} {cast.get('daypower', '')}".strip(),
                    ))
                # Cache only raw dicts
                raw_list = [f.model_dump(mode="json") for f in forecasts]
                cache_service.set(cache_key, raw_list, ttl=WEATHER_TTL)
                logger.info("天气查询成功: %s, %d 天", city, len(forecasts))
        except Exception as e:
            logger.warning("天气查询失败 city=%s: %s", city, e)
            return []

    # Filter by date range if provided
    if start_date and end_date:
        forecasts = [f for f in forecasts if start_date <= f.date <= end_date]
    elif start_date:
        forecasts = [f for f in forecasts if f.date >= start_date]
    elif end_date:
        forecasts = [f for f in forecasts if f.date <= end_date]

    return forecasts
