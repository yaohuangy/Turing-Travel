from datetime import date

import pytest

from app.database import Base, engine, get_session
from app.models.db_models import TripRecord
from app.services import storage_service

SAMPLE_ITINERARY = {
    "destination": "杭州",
    "start_date": "2026-06-01",
    "end_date": "2026-06-02",
    "days": [
        {
            "day_index": 0, "date": "2026-06-01", "weather": None,
            "spots": [{"name": "西湖", "address": "", "location": None, "visit_duration": "3小时", "description": "", "image_url": None, "poi_id": None}],
            "meals": [{"type": "breakfast", "name": "小笼包", "description": ""}, {"type": "lunch", "name": "西湖醋鱼", "description": ""}, {"type": "dinner", "name": "东坡肉", "description": ""}],
            "hotel": {"name": "西湖酒店", "location": "西湖区", "estimated_price": 400},
        }
    ],
    "budget": {"total": 2000, "transportation": 300, "accommodation": 400, "meals": 500, "tickets": 300, "other": 500},
}

TEST_USER = "test_user_abc"


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    session = get_session()
    session.query(TripRecord).delete()
    session.commit()
    session.close()


def test_save_and_get_by_id():
    trip_id = storage_service.save(
        name="杭州一日游", destination="杭州",
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 2),
        itinerary=SAMPLE_ITINERARY, user_id=TEST_USER,
    )
    assert trip_id is not None
    assert len(trip_id) == 36

    trip = storage_service.get_by_id(trip_id, user_id=TEST_USER)
    assert trip is not None
    assert trip["destination"] == "杭州"
    assert trip["trip_id"] == trip_id
    assert trip["name"] == "杭州一日游"
    assert trip["budget"]["total"] == 2000


def test_list_all():
    storage_service.save("Trip A", "北京", date(2026, 7, 1), date(2026, 7, 3), SAMPLE_ITINERARY, user_id=TEST_USER)
    storage_service.save("Trip B", "上海", date(2026, 8, 1), date(2026, 8, 4), SAMPLE_ITINERARY, user_id=TEST_USER)
    storage_service.save("Trip C", "三亚", date(2026, 9, 1), date(2026, 9, 3), SAMPLE_ITINERARY, user_id="other_user")
    # Only TEST_USER's trips
    trips = storage_service.list_all(user_id=TEST_USER)
    assert len(trips) == 2
    assert trips[0]["name"] == "Trip B"  # newest first


def test_delete():
    trip_id = storage_service.save("ToDelete", "成都", date(2026, 9, 1), date(2026, 9, 3), SAMPLE_ITINERARY, user_id=TEST_USER)
    assert storage_service.get_by_id(trip_id, user_id=TEST_USER) is not None
    # Wrong user can't delete
    assert storage_service.delete(trip_id, user_id="other_user") is False
    # Right user can
    assert storage_service.delete(trip_id, user_id=TEST_USER) is True
    assert storage_service.get_by_id(trip_id, user_id=TEST_USER) is None
    assert storage_service.delete("non-existent", user_id=TEST_USER) is False
