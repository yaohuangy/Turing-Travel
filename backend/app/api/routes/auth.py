import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_session
from app.models.db_models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory token store: token -> user_id
_token_store: dict[str, str] = {}


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _hash_password(password: str, salt: str = "") -> tuple[str, str]:
    """Hash a password with salt. Returns (hash, salt)."""
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def get_user_id_from_token(token: str) -> Optional[str]:
    return _token_store.get(token)


@router.post("/register")
def register(body: RegisterRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    session = get_session()
    try:
        existing = session.query(User).filter_by(username=body.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")

        h, salt = _hash_password(body.password)
        user = User(username=body.username, password_hash=f"{salt}:{h}")
        session.add(user)
        session.commit()
        return {"message": "注册成功", "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"注册失败: {e}")
    finally:
        session.close()


@router.post("/login")
def login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    session = get_session()
    try:
        user = session.query(User).filter_by(username=body.username).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # Verify password
        salt, stored_hash = user.password_hash.split(":", 1)
        h, _ = _hash_password(body.password, salt)
        if h != stored_hash:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # Generate token
        token = secrets.token_urlsafe(32)
        _token_store[token] = user.id

        return {"token": token, "username": user.username, "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {e}")
    finally:
        session.close()
