import json
import logging
from datetime import date, datetime
from typing import Optional

from app.database import get_session
from app.models.db_models import TripRecord

logger = logging.getLogger(__name__)


def _record_to_dict(r: TripRecord) -> dict:
    return {
        "trip_id": r.id,
        "name": r.name,
        "destination": r.destination,
        "start_date": r.start_date.isoformat() if isinstance(r.start_date, date) else str(r.start_date),
        "end_date": r.end_date.isoformat() if isinstance(r.end_date, date) else str(r.end_date),
        "total_budget": r.total_budget,
        "saved_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
    }


def save(
    name: str,
    destination: str,
    start_date: date,
    end_date: date,
    itinerary: dict,
) -> str:
    """Save a trip itinerary. Returns the trip_id."""
    budget = itinerary.get("budget", {})
    total_budget = budget.get("total", 0) if isinstance(budget, dict) else 0

    record = TripRecord(
        name=name,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        itinerary_json=json.dumps(itinerary, ensure_ascii=False),
        total_budget=float(total_budget),
    )
    session = get_session()
    try:
        session.add(record)
        session.commit()
        trip_id = record.id
        logger.info("Trip saved: id=%s, name=%s", trip_id, name)
        return trip_id
    except Exception as e:
        session.rollback()
        logger.error("Failed to save trip: %s", e)
        raise
    finally:
        session.close()


def get_by_id(trip_id: str) -> Optional[dict]:
    """Get a trip by ID. Returns the full itinerary dict with metadata, or None."""
    session = get_session()
    try:
        record = session.get(TripRecord, trip_id)
        if record is None:
            return None
        itinerary = json.loads(record.itinerary_json)
        itinerary["trip_id"] = record.id
        itinerary["name"] = record.name
        itinerary["saved_at"] = record.created_at.isoformat() if isinstance(record.created_at, datetime) else str(record.created_at)
        return itinerary
    except Exception as e:
        logger.error("Failed to get trip id=%s: %s", trip_id, e)
        raise
    finally:
        session.close()


def list_all() -> list[dict]:
    """List all saved trips (summary only)."""
    session = get_session()
    try:
        records = session.query(TripRecord).order_by(TripRecord.created_at.desc()).all()
        return [_record_to_dict(r) for r in records]
    except Exception as e:
        logger.error("Failed to list trips: %s", e)
        raise
    finally:
        session.close()


def delete(trip_id: str) -> bool:
    """Delete a trip. Returns True if deleted, False if not found."""
    session = get_session()
    try:
        record = session.get(TripRecord, trip_id)
        if record is None:
            return False
        session.delete(record)
        session.commit()
        logger.info("Trip deleted: id=%s", trip_id)
        return True
    except Exception as e:
        session.rollback()
        logger.error("Failed to delete trip id=%s: %s", trip_id, e)
        raise
    finally:
        session.close()
