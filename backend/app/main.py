"""FastAPI application entry point for LangNovel Studio."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.logger import setup_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
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
        message_max_chars=settings.log_message_max_chars,
    )
    logger.info("%s v%s starting", settings.app_name, settings.app_version)
    await task_service.cleanup_stale()

    # Wire MemoryManager into AnalysisPipeline for dual-write (SQL + ChromaDB)
    from app.memory.memory_manager import MemoryManager
    from app.services.analysis_pipeline import analysis_pipeline
    analysis_pipeline.set_memory_manager(MemoryManager())
    logger.info("AnalysisPipeline initialized with MemoryManager")

    # Load MCP plugins from DB (survive restarts)
    from app.services.mcp_service import mcp_service
    await mcp_service.load_from_db()
    logger.info("MCP plugins loaded from DB")

    logger.info("Application ready")
    yield
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
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
from app.api.polish import router as polish_router
from app.api.mcp_plugins import router as mcp_router
from app.api.book_import import router as book_import_router
from app.api.settings import router as settings_router
from app.api.prompt_templates import router as prompt_templates_router
from app.api.project_covers import router as project_covers_router
from app.api.graph_status import router as graph_status_router

app.include_router(settings_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(project_covers_router, prefix="/api")
app.include_router(wizard_router, prefix="/api")
app.include_router(inspiration_router, prefix="/api")
app.include_router(outlines_router, prefix="/api")
app.include_router(characters_router, prefix="/api")
app.include_router(careers_router, prefix="/api")
app.include_router(chapters_router, prefix="/api")
app.include_router(relationships_router, prefix="/api")
app.include_router(organizations_router, prefix="/api")
app.include_router(writing_styles_router, prefix="/api")
app.include_router(memories_router, prefix="/api")
app.include_router(foreshadows_router, prefix="/api")
app.include_router(mcp_router, prefix="/api")
app.include_router(prompt_templates_router, prefix="/api")
app.include_router(book_import_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(polish_router, prefix="/api")
app.include_router(graph_status_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}
