from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_config():
    return {"amap_js_key": settings.AMAP_API_KEY}
