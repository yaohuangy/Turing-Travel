import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


async def _register_and_login(
    client: AsyncClient, username: str = "testuser", password: str = "test1234"
) -> tuple[str, str]:
    """Register a user and login. Returns (user_id, token)."""
    resp = await client.post("/api/auth/register", json={
        "username": username, "password": password,
    })
    # 409 (already exists) is fine
    if resp.status_code not in (200, 409):
        raise RuntimeError(f"Register failed: {resp.status_code} {resp.text}")

    resp = await client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    return data["user_id"], data["token"]


async def get_auth_headers(client: AsyncClient) -> dict:
    """Get Authorization header dict for a test user."""
    _, token = await _register_and_login(client)
    return {"Authorization": f"Bearer {token}"}
