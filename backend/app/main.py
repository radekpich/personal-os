import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes.agent_actions import router as agent_actions_router
from app.api.routes.attachments import router as attachments_router
from app.api.routes.attachments import storage_router, task_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.categories import router as categories_router
from app.api.routes.challenges import router as challenges_router
from app.api.routes.contexts import router as contexts_router
from app.api.routes.health import router as health_router
from app.api.routes.notes import router as notes_router
from app.api.routes.tags import router as tags_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.visions import router as visions_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import CSRFCookieMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.db.session import AsyncSessionLocal
from app.services.agent_action_service import AgentActionAuditMiddleware
from app.services.attachment_service import cleanup_deleted_and_orphaned_files

configure_logging()
logger = logging.getLogger("app")
settings = get_settings()

scheduler = AsyncIOScheduler(timezone="Europe/Prague")


async def run_attachment_cleanup() -> None:
    result = await cleanup_deleted_and_orphaned_files(AsyncSessionLocal, settings)
    logger.info("attachment cleanup finished", extra=result)


def start_scheduler() -> None:
    if settings.environment == "test" or scheduler.running:
        return
    scheduler.add_job(
        run_attachment_cleanup,
        trigger="cron",
        hour=3,
        minute=20,
        id="attachment_cleanup",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="Personal OS Backend", lifespan=lifespan)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return _rate_limit_exceeded_handler(request, exc)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(AgentActionAuditMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFCookieMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(agent_actions_router)
app.include_router(attachments_router)
app.include_router(storage_router)
app.include_router(task_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(categories_router)
app.include_router(challenges_router)
app.include_router(contexts_router)
app.include_router(notes_router)
app.include_router(tags_router)
app.include_router(tasks_router)
app.include_router(visions_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )
