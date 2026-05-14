import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import WeatherInfo
from app.services.weather_service import get_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/forecast", response_model=List[WeatherInfo])
async def forecast(
    city: str = Query(..., min_length=1, description="城市名称，如：杭州、大理"),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
):
    try:
        logger.info("GET /api/weather/forecast: city=%s", city)
        result = await get_forecast(city, start_date, end_date)
        return result
    except Exception as e:
        logger.error("Weather forecast error: %s", e)
        raise HTTPException(status_code=500, detail=f"天气查询失败: {e}")
