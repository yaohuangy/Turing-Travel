from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from tests.conftest import get_auth_headers

MOCK_ITINERARY = {
    "destination": "大理",
    "start_date": "2026-06-01",
    "end_date": "2026-06-03",
    "days": [
        {
            "day_index": 0, "date": "2026-06-01", "weather": None,
            "spots": [{"name": "洱海", "address": "", "location": None, "visit_duration": "3小时", "description": "洱海是大理的标志性景点", "image_url": None, "poi_id": None}],
            "meals": [
                {"type": "breakfast", "name": "米线", "description": "云南米线"},
                {"type": "lunch", "name": "白族菜", "description": "当地特色"},
                {"type": "dinner", "name": "火锅", "description": "菌子火锅"},
            ],
            "hotel": {"name": "大理古城客栈", "location": "大理古城", "estimated_price": 300},
        },
        {
            "day_index": 1, "date": "2026-06-02", "weather": None,
            "spots": [{"name": "崇圣寺三塔", "address": "", "location": None, "visit_duration": "2小时", "description": "大理著名的佛教建筑", "image_url": None, "poi_id": None}],
            "meals": [
                {"type": "breakfast", "name": "饵丝", "description": "大理特色"},
                {"type": "lunch", "name": "素斋", "description": "寺庙素斋"},
                {"type": "dinner", "name": "烧烤", "description": "云南烧烤"},
            ],
            "hotel": {"name": "大理古城客栈", "location": "大理古城", "estimated_price": 300},
        },
    ],
    "budget": {"total": 2400, "transportation": 400, "accommodation": 600, "meals": 600, "tickets": 400, "other": 400},
}


@pytest.mark.anyio
async def test_generate_trip_success():
    transport = ASGITransport(app=app)
    body = {
        "destination": "大理",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "budget_level": "comfort",
        "travelers": 2,
        "preferences": ["自然风光", "美食探店"],
        "extra_requirements": "多安排洱海边的景点",
    }
    mock_fn = AsyncMock(return_value=MOCK_ITINERARY)
    with patch("app.api.routes.trip.generate_full_trip", mock_fn):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await get_auth_headers(client)
            resp = await client.post("/api/trip/generate", json=body, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["itinerary"]["destination"] == "大理"
        assert len(data["itinerary"]["days"]) == 2
