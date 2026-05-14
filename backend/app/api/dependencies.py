from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.routes.auth import get_user_id_from_token

security = HTTPBearer(auto_error=False)


def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    """Extract user_id from Bearer token. Raises 401 if missing or invalid."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")
    user_id = get_user_id_from_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user_id
