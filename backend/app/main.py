import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.workspace import router as workspace_router
from app.services import http_client
from app.exceptions import NovelSmithError
from app.services.workspace_manager import ensure_workspace_initialized

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("novelsmith.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared HTTP client and workspace
    logger.info("Starting up NovelSmith API...")
    await http_client.startup()
    try:
        ensure_workspace_initialized()
        logger.info("NovelSmith 工作区初始化成功")
    except Exception as e:
        logger.exception("Failed to initialize workspace")
    yield
    # Shutdown: Close shared HTTP client
    logger.info("Shutting down NovelSmith API...")
    await http_client.shutdown()


app = FastAPI(
    title="NovelSmith Agent API", 
    version="0.1.0",
    lifespan=lifespan
)

# CORS Origins Setup
cors_origins_env = os.getenv("NOVELSMITH_CORS_ORIGINS")
if cors_origins_env:
    allow_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    logger.info(f"Loaded CORS origins from environment: {allow_origins}")
else:
    allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8765"]
    logger.info(f"Using default CORS origins: {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NovelSmithError)
async def novelsmith_exception_handler(request: Request, exc: NovelSmithError):
    logger.error(f"NovelSmithError: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"ok": False, "message": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "message": f"服务器内部错误: {str(exc)}"},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "novelsmith-agent"}


app.include_router(agent_router, prefix="/api/agent", tags=["agent"])
app.include_router(workspace_router, prefix="/api/workspace", tags=["workspace"])
