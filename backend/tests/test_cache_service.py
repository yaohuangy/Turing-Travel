from unittest.mock import MagicMock, patch

from app.services import cache_service


def test_get_returns_none_when_redis_unavailable():
    with patch.object(cache_service, "_get_redis", return_value=None):
        result = cache_service.get("test_key")
        assert result is None


def test_set_no_error_when_redis_unavailable():
    with patch.object(cache_service, "_get_redis", return_value=None):
        cache_service.set("test_key", {"a": 1}, ttl=60)


def test_get_returns_cached_value():
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"lng": 100.0, "lat": 25.0}'
    with patch.object(cache_service, "_get_redis", return_value=mock_redis):
        result = cache_service.get("geocode:大理")
        assert result == {"lng": 100.0, "lat": 25.0}


def test_set_calls_redis_setex():
    mock_redis = MagicMock()
    with patch.object(cache_service, "_get_redis", return_value=mock_redis):
        cache_service.set("geocode:大理", {"lng": 100.0, "lat": 25.0}, ttl=3600)
        mock_redis.setex.assert_called_once()


def test_get_handles_redis_error():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = OSError("connection lost")
    with patch.object(cache_service, "_get_redis", return_value=mock_redis):
        result = cache_service.get("test_key")
        assert result is None
