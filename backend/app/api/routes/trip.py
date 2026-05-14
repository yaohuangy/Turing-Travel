import logging
from datetime import date

from fastapi import APIRouter, HTTPException

from app.models.schemas import EditRequest, GenerateResponse, Itinerary, SaveRequest, TripRequest
from app.services import storage_service
from app.services.trip_service import edit_day, generate_full_trip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trip", tags=["trip"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_trip(request: TripRequest):
    try:
        logger.info("POST /api/trip/generate: destination=%s", request.destination)
        raw = await generate_full_trip(request)
        itinerary = Itinerary(**raw)
        return GenerateResponse(itinerary=itinerary, raw=None)
    except RuntimeError as e:
        logger.error("Trip generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in trip generation: %s", e)
        raise HTTPException(status_code=500, detail=f"行程生成失败: {e}")


@router.post("/save")
async def save_trip(request: SaveRequest):
    try:
        trip_id = storage_service.save(
            name=request.name,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            itinerary=request.itinerary,
        )
        return {"trip_id": trip_id}
    except Exception as e:
        logger.error("Failed to save trip: %s", e)
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")




@router.get("/trip/{trip_id}")
async def get_trip(trip_id: str):
    try:
        trip = storage_service.get_by_id(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="行程不存在")
        return trip
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get trip id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.post("/edit")
async def edit_trip(request: EditRequest):
    try:
        logger.info(
            "POST /api/trip/edit: trip_id=%s, day_index=%d, instruction=%s",
            request.trip_id, request.day_index, request.edit_instruction[:60],
        )
        result = await edit_day(request.trip_id, request.day_index, request.edit_instruction)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error("Trip edit failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in trip edit: %s", e)
        raise HTTPException(status_code=500, detail=f"行程编辑失败: {e}")


@router.delete("/trip/{trip_id}")
async def delete_trip(trip_id: str):
    try:
        deleted = storage_service.delete(trip_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="行程不存在")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete trip id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")
