import logging
from typing import Optional

import httpx

from app.config import settings
from app.services import cache_service

logger = logging.getLogger(__name__)

AMAP_BASE = "https://restapi.amap.com/v3"
GEOCODE_TTL = 0  # permanent
POI_TTL = 86400  # 24 hours
ROUTE_TTL = 3600  # 1 hour


async def geocode(address: str) -> Optional[tuple[float, float]]:
    """Geocode an address to (lng, lat). Returns None on failure."""
    cache_key = f"geocode:{address}"
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("从缓存读取地理编码: %s", address)
        return cached["lng"], cached["lat"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{AMAP_BASE}/geocode/geo",
                params={"key": settings.AMAP_API_KEY, "address": address},
            )
            resp.raise_for_status()
            data = resp.json()
            geocodes = data.get("geocodes", [])
            if geocodes and geocodes[0].get("location"):
                loc_str = geocodes[0]["location"]  # "lng,lat"
                lng_str, lat_str = loc_str.split(",")
                lng, lat = float(lng_str), float(lat_str)
                cache_service.set(cache_key, {"lng": lng, "lat": lat}, ttl=GEOCODE_TTL)
                logger.info("地理编码成功: %s -> (%.6f, %.6f)", address, lng, lat)
                return lng, lat
            logger.warning("地理编码无结果: %s", address)
            return None
    except Exception as e:
        logger.warning("地理编码失败 address=%s: %s", address, e)
        return None


async def search_poi(keyword: str, city: str) -> Optional[dict]:
    """Search for a POI and return {name, address, location: {lng, lat}, poi_id}."""
    cache_key = f"poi:{keyword}:{city}"
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("从缓存读取POI: %s (%s)", keyword, city)
        return cached

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{AMAP_BASE}/place/text",
                params={
                    "key": settings.AMAP_API_KEY,
                    "keywords": keyword,
                    "city": city,
                    "offset": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            pois = data.get("pois", [])
            if pois:
                poi = pois[0]
                loc_str = poi.get("location", "")
                lng, lat = (0.0, 0.0)
                if loc_str:
                    parts = loc_str.split(",")
                    lng, lat = float(parts[0]), float(parts[1])
                result = {
                    "name": poi.get("name", keyword),
                    "address": poi.get("address", ""),
                    "location": {"lng": lng, "lat": lat},
                    "poi_id": poi.get("id"),
                }
                cache_service.set(cache_key, result, ttl=POI_TTL)
                logger.info("POI搜索成功: %s -> %s", keyword, result["name"])
                return result
            logger.warning("POI搜索无结果: %s (%s)", keyword, city)
            return None
    except Exception as e:
        logger.warning("POI搜索失败 keyword=%s city=%s: %s", keyword, city, e)
        return None


async def route_driving(
    origin: tuple[float, float], dest: tuple[float, float]
) -> Optional[dict]:
    """Get driving route between two points. Returns {distance_km, duration_min}."""
    origin_str = f"{origin[0]},{origin[1]}"
    dest_str = f"{dest[0]},{dest[1]}"
    cache_key = f"route:{origin_str}:{dest_str}"
    cached = cache_service.get(cache_key)
    if cached:
        logger.info("从缓存读取路线: %s -> %s", origin_str, dest_str)
        return cached

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{AMAP_BASE}/direction/driving",
                params={
                    "key": settings.AMAP_API_KEY,
                    "origin": origin_str,
                    "destination": dest_str,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            paths = data.get("route", {}).get("paths", [])
            if paths:
                path = paths[0]
                distance_m = int(path.get("distance", 0))
                duration_s = int(path.get("duration", 0))
                result = {
                    "distance_km": round(distance_m / 1000, 1),
                    "duration_min": max(1, round(duration_s / 60)),
                }
                cache_service.set(cache_key, result, ttl=ROUTE_TTL)
                logger.info(
                    "路线规划成功: %s -> %s: %.1f km, %d min",
                    origin_str, dest_str, result["distance_km"], result["duration_min"],
                )
                return result
            logger.warning("路线规划无结果: %s -> %s", origin_str, dest_str)
            return None
    except Exception as e:
        logger.warning("路线规划失败: %s -> %s: %s", origin_str, dest_str, e)
        return None
