import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user_id
from app.models.schemas import EditRequest, GenerateResponse, Itinerary, SaveRequest, TripRequest
from app.services import storage_service
from app.services.trip_service import edit_day, generate_full_trip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trip", tags=["trip"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_trip(request: TripRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info("POST /api/trip/generate: destination=%s, user=%s", request.destination, user_id)
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
async def save_trip(request: SaveRequest, user_id: str = Depends(get_current_user_id)):
    try:
        trip_id = storage_service.save(
            name=request.name,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            itinerary=request.itinerary,
            user_id=user_id,
        )
        return {"trip_id": trip_id}
    except Exception as e:
        logger.error("Failed to save trip: %s", e)
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")


@router.get("/trip/{trip_id}")
async def get_trip(trip_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        trip = storage_service.get_by_id(trip_id, user_id=user_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="行程不存在")
        return trip
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get trip id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.post("/edit")
async def edit_trip(request: EditRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(
            "POST /api/trip/edit: trip_id=%s, day_index=%d, user=%s",
            request.trip_id, request.day_index, user_id,
        )
        result = await edit_day(request.trip_id, request.day_index, request.edit_instruction, user_id)
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
async def delete_trip(trip_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        deleted = storage_service.delete(trip_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="行程不存在")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete trip id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")
