from httpx import ASGITransport, AsyncClient
import pytest
from app.api.main import app


@pytest.mark.anyio
async def test_root_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
