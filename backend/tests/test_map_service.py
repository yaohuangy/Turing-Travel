from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import map_service


def _make_mock_response(json_data):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = lambda: None
    return mock_resp


def _patch_http(mock_resp):
    """Patch httpx.AsyncClient to return a mock with the given response."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return patch.object(map_service.httpx, "AsyncClient", return_value=mock_client)


@pytest.mark.anyio
async def test_geocode_returns_coordinates():
    mock_resp = _make_mock_response({"geocodes": [{"location": "100.225456,25.684321"}]})
    with patch.object(map_service.cache_service, "get", return_value=None):
        with patch.object(map_service.cache_service, "set"):
            with _patch_http(mock_resp):
                result = await map_service.geocode("大理古城")
                assert result == (100.225456, 25.684321)


@pytest.mark.anyio
async def test_geocode_returns_none_on_empty_result():
    mock_resp = _make_mock_response({"geocodes": []})
    with patch.object(map_service.cache_service, "get", return_value=None):
        with _patch_http(mock_resp):
            result = await map_service.geocode("不存在的地址XYZ")
            assert result is None


@pytest.mark.anyio
async def test_geocode_uses_cache():
    with patch.object(map_service.cache_service, "get", return_value={"lng": 100.0, "lat": 25.0}):
        result = await map_service.geocode("大理")
        assert result == (100.0, 25.0)


@pytest.mark.anyio
async def test_search_poi_returns_details():
    mock_resp = _make_mock_response({
        "pois": [{
            "name": "洱海",
            "address": "云南省大理白族自治州大理市",
            "location": "100.225456,25.684321",
            "id": "B0FFG9XXXX",
        }]
    })
    with patch.object(map_service.cache_service, "get", return_value=None):
        with patch.object(map_service.cache_service, "set"):
            with _patch_http(mock_resp):
                result = await map_service.search_poi("洱海", "大理")
                assert result is not None
                assert result["name"] == "洱海"
                assert result["location"]["lng"] == 100.225456
                assert result["poi_id"] == "B0FFG9XXXX"


@pytest.mark.anyio
async def test_route_driving_returns_distance_duration():
    mock_resp = _make_mock_response({
        "route": {"paths": [{"distance": "15200", "duration": "1800"}]}
    })
    with patch.object(map_service.cache_service, "get", return_value=None):
        with patch.object(map_service.cache_service, "set"):
            with _patch_http(mock_resp):
                result = await map_service.route_driving((100.0, 25.0), (100.5, 25.5))
                assert result is not None
                assert result["distance_km"] == 15.2
                assert result["duration_min"] == 30


@pytest.mark.anyio
async def test_route_driving_handles_api_error():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=OSError("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch.object(map_service.httpx, "AsyncClient", return_value=mock_client):
        with patch.object(map_service.cache_service, "get", return_value=None):
            result = await map_service.route_driving((100.0, 25.0), (100.5, 25.5))
            assert result is None
