"""FastAPI application entry point for GraphNovel."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware, get_request_id
from app.middleware.rate_limit import InMemoryRateLimitMiddleware
from app.errors import AppError
from app.schemas.response import ApiResponse
from app.services.task_service import task_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    setup_logging(
        level=settings.log_level,
        log_to_file=settings.log_to_file,
        log_file_path=settings.log_file_path,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )
    logger.info("%s v%s starting", settings.app_name, settings.app_version)

    # Security: check for insecure defaults
    warnings = settings.check_security()
    for w in warnings:
        logger.warning("SECURITY: %s", w)

    # Initialize database engine eagerly (needed by modules using async_session_factory)
    from app.database import _init_factory
    await _init_factory()

    await task_service.cleanup_stale()

    # Wire MemoryManager into AnalysisPipeline for dual-write (SQL + ChromaDB)
    from app.memory.memory_manager import memory_manager
    from app.services.analysis_pipeline import analysis_pipeline
    analysis_pipeline.set_memory_manager(memory_manager)
    logger.info("AnalysisPipeline initialized with MemoryManager")

    # Load MCP plugins from DB (survive restarts)
    from app.mcp import mcp_client, register_status_sync
    await mcp_client.initialize()
    register_status_sync()
    from app.services.mcp_service import mcp_service
    await mcp_service.load_from_db()
    logger.info("MCP facade initialized and plugins loaded from DB")

    logger.info("Application ready")
    yield
    # Shutdown (ordered sequence)
    logger.info("Shutting down...")
    from app.mcp import shutdown_status_sync
    try:
        await mcp_client.close()
    except Exception as e:
        logger.error("MCP close error: %s", e)
    try:
        await shutdown_status_sync()
    except Exception as e:
        logger.error("MCP status sync shutdown error: %s", e)


app = FastAPI(
    title="GraphNovel API",
    version=settings.app_version,
    description="GraphNovel - AI-powered novel writing platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Middleware (order matters: last added = first to execute)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(InMemoryRateLimitMiddleware, requests_per_minute=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ──────────────────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle known application errors with structured response."""
    logger.warning(
        "AppError: code=%d message=%s detail=%s",
        exc.code, exc.message, exc.detail,
    )
    return JSONResponse(
        status_code=exc.code,
        content=ApiResponse.error(
            code=exc.code,
            message=exc.message,
            request_id=get_request_id(),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors. Hides internal details in production."""
    request_id = get_request_id()
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(
            code=500,
            message="Internal server error" if not settings.debug else str(exc),
            request_id=request_id,
        ).model_dump(),
    )


# Register API routers
from app.api.projects import router as projects_router
from app.api.chapters import router as chapters_router
from app.api.outlines import router as outlines_router
from app.api.characters import router as characters_router
from app.api.relationships import router as relationships_router
from app.api.organizations import router as organizations_router
from app.api.careers import router as careers_router
from app.api.writing_styles import router as writing_styles_router
from app.api.foreshadows import router as foreshadows_router
from app.api.memories import router as memories_router
from app.api.inspiration import router as inspiration_router
from app.api.skills import router as skills_router
from app.api.tasks import router as tasks_router
from app.api.wizard_stream import router as wizard_router
from app.api.mcp_plugins import router as mcp_router
from app.api.book_import import router as book_import_router
from app.api.settings import router as settings_router
from app.api.prompt_templates import router as prompt_templates_router
from app.api.project_covers import router as project_covers_router
from app.api.graph_status import router as graph_status_router
from app.api.mcp_admin import router as mcp_admin_router

API_PREFIX = "/api"

app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(projects_router, prefix=API_PREFIX)
app.include_router(project_covers_router, prefix=API_PREFIX)
app.include_router(wizard_router, prefix=API_PREFIX)
app.include_router(inspiration_router, prefix=API_PREFIX)
app.include_router(outlines_router, prefix=API_PREFIX)
app.include_router(characters_router, prefix=API_PREFIX)
app.include_router(careers_router, prefix=API_PREFIX)
app.include_router(chapters_router, prefix=API_PREFIX)
app.include_router(relationships_router, prefix=API_PREFIX)
app.include_router(organizations_router, prefix=API_PREFIX)
app.include_router(writing_styles_router, prefix=API_PREFIX)
app.include_router(memories_router, prefix=API_PREFIX)
app.include_router(foreshadows_router, prefix=API_PREFIX)
app.include_router(mcp_router, prefix=API_PREFIX)
app.include_router(prompt_templates_router, prefix=API_PREFIX)
app.include_router(book_import_router, prefix=API_PREFIX)
app.include_router(skills_router, prefix=API_PREFIX)
app.include_router(tasks_router, prefix=API_PREFIX)
app.include_router(graph_status_router, prefix=API_PREFIX)
app.include_router(mcp_admin_router, prefix=API_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


@app.get("/api/info")
async def generation_info():
    """查看当前正在运行的 AI 生成任务和进度。"""
    from app.services.generation_tracker import tracker as gen_tracker
    active = gen_tracker.snapshot()
    return {
        "active_count": len(active),
        "active": active,
        "server_time": __import__("datetime").datetime.now().isoformat(),
    }
