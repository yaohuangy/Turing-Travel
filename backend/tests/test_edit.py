"""Tests for the single-day edit feature."""
import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.database import Base, engine, get_session
from app.models.db_models import TripRecord
from app.services import storage_service

SAMPLE_TRIP = {
    "destination": "杭州",
    "start_date": "2026-06-01",
    "end_date": "2026-06-03",
    "days": [
        {
            "day_index": 0,
            "date": "2026-06-01",
            "weather": None,
            "spots": [
                {"name": "西湖", "address": "", "location": None, "visit_duration": "3小时", "description": "", "image_url": None, "poi_id": None},
                {"name": "灵隐寺", "address": "", "location": None, "visit_duration": "2小时", "description": "", "image_url": None, "poi_id": None},
            ],
            "meals": [
                {"type": "breakfast", "name": "小笼包", "description": ""},
                {"type": "lunch", "name": "西湖醋鱼", "description": ""},
                {"type": "dinner", "name": "东坡肉", "description": ""},
            ],
            "hotel": {"name": "杭州酒店", "location": "西湖区", "estimated_price": 400},
        },
        {
            "day_index": 1,
            "date": "2026-06-02",
            "weather": None,
            "spots": [
                {"name": "西溪湿地", "address": "", "location": None, "visit_duration": "3小时", "description": "", "image_url": None, "poi_id": None},
            ],
            "meals": [
                {"type": "breakfast", "name": "葱包桧", "description": ""},
                {"type": "lunch", "name": "片儿川", "description": ""},
                {"type": "dinner", "name": "叫花鸡", "description": ""},
            ],
            "hotel": {"name": "杭州酒店", "location": "西湖区", "estimated_price": 400},
        },
    ],
    "budget": {"total": 2000, "transportation": 300, "accommodation": 800, "meals": 500, "tickets": 200, "other": 200},
}

# Edited day 0: lunch changed to 火锅
EDITED_DAY_0 = {
    "day_index": 0,
    "date": "2026-06-01",
    "weather": None,
    "spots": [
        {"name": "西湖", "address": "", "location": None, "visit_duration": "3小时", "description": "", "image_url": None, "poi_id": None},
        {"name": "灵隐寺", "address": "", "location": None, "visit_duration": "2小时", "description": "", "image_url": None, "poi_id": None},
    ],
    "meals": [
        {"type": "breakfast", "name": "小笼包", "description": ""},
        {"type": "lunch", "name": "火锅", "description": "改为火锅"},
        {"type": "dinner", "name": "东坡肉", "description": ""},
    ],
    "hotel": {"name": "杭州酒店", "location": "西湖区", "estimated_price": 400},
}


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    session = get_session()
    session.query(TripRecord).delete()
    session.commit()
    session.close()


@pytest.mark.anyio
async def test_edit_changes_lunch():
    # Save a trip first
    trip_id = storage_service.save(
        name="杭州二日游",
        destination="杭州",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        itinerary=SAMPLE_TRIP,
    )

    transport = ASGITransport(app=app)

    # Mock the LLM call to return the edited day
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.output = AsyncMock()
    mock_resp.output.choices = [AsyncMock()]
    mock_resp.output.choices[0].message = AsyncMock()
    mock_resp.output.choices[0].message.content = json.dumps(EDITED_DAY_0, ensure_ascii=False)
    mock_resp.usage = AsyncMock(input_tokens=100, output_tokens=200)

    with patch("app.services.trip_service.Generation.call", return_value=mock_resp):
        with patch("app.services.trip_service.map_service.search_poi", new_callable=AsyncMock) as mock_poi:
            with patch("app.services.trip_service.map_service.route_driving", new_callable=AsyncMock) as mock_route:
                mock_poi.return_value = None  # no POI data
                mock_route.return_value = None

                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/api/trip/edit", json={
                        "trip_id": trip_id,
                        "day_index": 0,
                        "edit_instruction": "把午餐换成火锅",
                    })
                    assert resp.status_code == 200
                    data = resp.json()
                    # Day 0 lunch should be 火锅
                    day0 = data["days"][0]
                    lunch = [m for m in day0["meals"] if m["type"] == "lunch"][0]
                    assert lunch["name"] == "火锅"
                    # Day 1 should be unchanged
                    day1 = data["days"][1]
                    lunch1 = [m for m in day1["meals"] if m["type"] == "lunch"][0]
                    assert lunch1["name"] == "片儿川"


@pytest.mark.anyio
async def test_edit_trip_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/trip/edit", json={
            "trip_id": "00000000-0000-0000-0000-000000000000",
            "day_index": 0,
            "edit_instruction": "把午餐换成火锅",
        })
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_edit_invalid_day_index():
    trip_id = storage_service.save(
        name="杭州二日游",
        destination="杭州",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        itinerary=SAMPLE_TRIP,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/trip/edit", json={
            "trip_id": trip_id,
            "day_index": 99,
            "edit_instruction": "把午餐换成火锅",
        })
        assert resp.status_code == 404
