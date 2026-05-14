from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import weather_service


MOCK_FORECAST_RESP = {
    "forecasts": [{
        "city": "杭州市",
        "adcode": "330100",
        "casts": [
            {
                "date": "2026-05-15",
                "dayweather": "晴",
                "nightweather": "多云",
                "daytemp": "28",
                "nighttemp": "18",
                "daywind": "东南",
                "daypower": "≤3",
            },
            {
                "date": "2026-05-16",
                "dayweather": "多云",
                "nightweather": "阴",
                "daytemp": "26",
                "nighttemp": "17",
                "daywind": "东北",
                "daypower": "≤3",
            },
        ]
    }]
}


def _make_mock_response(json_data):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = lambda: None
    return mock_resp


def _patch_http(mock_resp):
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return patch.object(weather_service.httpx, "AsyncClient", return_value=mock_client)


@pytest.mark.anyio
async def test_get_forecast_returns_daily_weather():
    mock_resp = _make_mock_response(MOCK_FORECAST_RESP)
    with patch.object(weather_service.cache_service, "get", return_value=None):
        with patch.object(weather_service.cache_service, "set"):
            with _patch_http(mock_resp):
                result = await weather_service.get_forecast("杭州")
                assert len(result) == 2
                assert result[0].condition == "晴"
                assert result[0].temp_high == 28.0
                assert result[0].temp_low == 18.0
                assert result[0].wind == "东南 ≤3"
                assert result[1].condition == "多云"


@pytest.mark.anyio
async def test_get_forecast_filters_by_date_range():
    mock_resp = _make_mock_response(MOCK_FORECAST_RESP)
    from datetime import date
    with patch.object(weather_service.cache_service, "get", return_value=None):
        with patch.object(weather_service.cache_service, "set"):
            with _patch_http(mock_resp):
                result = await weather_service.get_forecast(
                    "杭州",
                    start_date=date(2026, 5, 16),
                    end_date=date(2026, 5, 16),
                )
                assert len(result) == 1
                assert result[0].condition == "多云"


@pytest.mark.anyio
async def test_get_forecast_uses_cache():
    cached_data = [
        {"date": "2026-05-15", "condition": "晴", "temp_high": 28.0, "temp_low": 18.0, "wind": "东南 ≤3"},
    ]
    with patch.object(weather_service.cache_service, "get", return_value=cached_data):
        result = await weather_service.get_forecast("杭州")
        assert len(result) == 1
        assert result[0].condition == "晴"


@pytest.mark.anyio
async def test_get_forecast_handles_api_error():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=OSError("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch.object(weather_service.httpx, "AsyncClient", return_value=mock_client):
        with patch.object(weather_service.cache_service, "get", return_value=None):
            result = await weather_service.get_forecast("杭州")
            assert result == []


@pytest.mark.anyio
async def test_forecast_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.api.main import app

    mock_resp = _make_mock_response(MOCK_FORECAST_RESP)
    with patch.object(weather_service.cache_service, "get", return_value=None):
        with patch.object(weather_service.cache_service, "set"):
            with _patch_http(mock_resp):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/weather/forecast?city=杭州")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert len(data) == 2
                    assert data[0]["condition"] == "晴"
                    assert data[0]["temp_high"] == 28.0
