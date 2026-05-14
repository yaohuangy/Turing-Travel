import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_user_id
from app.api.routes.auth import router as auth_router
from app.api.routes.config import router as config_router
from app.api.routes.export import router as export_router
from app.api.routes.trip import router as trip_router
from app.api.routes.weather import router as weather_router
from app.config import settings
from app.database import Base, engine
from app.services import storage_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Turing Travel API starting up (log level: %s)", settings.LOG_LEVEL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    # Auto-index travel guides in background thread
    try:
        from rag.vector_db import add_documents
        threading.Thread(target=add_documents, daemon=True).start()
        logger.info("Background guide indexing started")
    except Exception as e:
        logger.warning("Failed to start guide indexing: %s", e)
    yield


app = FastAPI(title="Turing Travel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(trip_router)
app.include_router(weather_router)
app.include_router(export_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )


@app.get("/api/trips")
async def list_trips(user_id: str = Depends(get_current_user_id)):
    try:
        return storage_service.list_all(user_id=user_id)
    except Exception as e:
        logger.error("Failed to list trips: %s", e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"status": "ok"}
