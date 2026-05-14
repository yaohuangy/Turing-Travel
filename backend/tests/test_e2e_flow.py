from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.database import Base, engine, get_session
from app.models.db_models import TripRecord
from tests.conftest import get_auth_headers

MOCK_LLM_ITINERARY = {
    "destination": "杭州", "start_date": "2026-06-01", "end_date": "2026-06-02",
    "days": [
        {
            "day_index": 0, "date": "2026-06-01", "weather": None,
            "spots": [
                {"name": "西湖", "address": "", "location": None, "visit_duration": "3小时", "description": "世界文化遗产", "image_url": None, "poi_id": None},
                {"name": "灵隐寺", "address": "", "location": None, "visit_duration": "2小时", "description": "千年古刹", "image_url": None, "poi_id": None},
            ],
            "meals": [
                {"type": "breakfast", "name": "小笼包", "description": ""},
                {"type": "lunch", "name": "西湖醋鱼", "description": ""},
                {"type": "dinner", "name": "东坡肉", "description": ""},
            ],
            "hotel": {"name": "杭州酒店", "location": "西湖区", "estimated_price": 400},
        }
    ],
    "budget": {"total": 2000, "transportation": 300, "accommodation": 400, "meals": 500, "tickets": 300, "other": 500},
}

MOCK_POI = {"name": "西湖", "address": "浙江省杭州市西湖区", "location": {"lng": 120.141, "lat": 30.238}, "poi_id": "B0FFG9XXXX"}
MOCK_ROUTE = {"distance_km": 5.5, "duration_min": 15}
MOCK_WEATHER = [{"date": "2026-06-01", "condition": "晴", "temp_high": 28, "temp_low": 18, "wind": "东南 ≤3"}]


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    session = get_session()
    session.query(TripRecord).delete()
    session.commit()
    session.close()


@pytest.mark.anyio
async def test_full_e2e_flow():
    transport = ASGITransport(app=app)

    with patch("app.agents.trip_planner_agent.generate_itinerary", return_value=MOCK_LLM_ITINERARY):
        with patch("app.services.map_service.search_poi", new_callable=AsyncMock) as mock_poi:
            with patch("app.services.map_service.route_driving", new_callable=AsyncMock) as mock_route:
                with patch("app.services.weather_service.get_forecast", new_callable=AsyncMock) as mock_weather:
                    mock_poi.return_value = MOCK_POI
                    mock_route.return_value = MOCK_ROUTE
                    mock_weather.return_value = MOCK_WEATHER

                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        h = await get_auth_headers(client)

                        # 1. Generate trip
                        gen_body = {"destination": "杭州", "start_date": "2026-06-01", "end_date": "2026-06-02", "budget_level": "comfort", "travelers": 2, "preferences": ["自然风光"], "extra_requirements": None}
                        resp = await client.post("/api/trip/generate", json=gen_body, headers=h)
                        assert resp.status_code == 200
                        data = resp.json()
                        assert data["itinerary"]["destination"] == "杭州"
                        assert len(data["itinerary"]["days"]) == 1
                        itinerary = data["itinerary"]

                        # 2. Save trip
                        save_body = {"name": "杭州一日游", "destination": "杭州", "start_date": "2026-06-01", "end_date": "2026-06-02", "itinerary": itinerary}
                        resp = await client.post("/api/trip/save", json=save_body, headers=h)
                        assert resp.status_code == 200
                        trip_id = resp.json()["trip_id"]
                        assert len(trip_id) == 36

                        # 3. List trips
                        resp = await client.get("/api/trips", headers=h)
                        assert resp.status_code == 200
                        trips = resp.json()
                        assert len(trips) == 1
                        assert trips[0]["trip_id"] == trip_id
                        assert trips[0]["destination"] == "杭州"

                        # 4. Get trip detail
                        resp = await client.get(f"/api/trip/trip/{trip_id}", headers=h)
                        assert resp.status_code == 200
                        detail = resp.json()
                        assert detail["destination"] == "杭州"
                        assert "days" in detail

                        # 5. Export Markdown
                        resp = await client.get(f"/api/export/{trip_id}/markdown")
                        assert resp.status_code == 200
                        assert resp.headers["content-type"].startswith("text/markdown")
                        assert "# 杭州" in resp.text
                        assert "西湖" in resp.text

                        # 6. Export PDF
                        resp = await client.get(f"/api/export/{trip_id}/pdf")
                        assert resp.status_code == 200
                        assert resp.headers["content-type"] == "application/pdf"
                        assert resp.content[:4] == b"%PDF"

                        # 7. Delete trip
                        resp = await client.delete(f"/api/trip/trip/{trip_id}", headers=h)
                        assert resp.status_code == 200
                        assert resp.json()["deleted"] is True

                        # 8. Verify deleted
                        resp = await client.get("/api/trips", headers=h)
                        assert resp.status_code == 200
                        assert len(resp.json()) == 0
