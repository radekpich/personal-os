import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.categories import router as categories_router
from app.api.routes.contexts import router as contexts_router
from app.api.routes.health import router as health_router
from app.api.routes.tags import router as tags_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import CSRFCookieMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger("app")
settings = get_settings()

app = FastAPI(title="Personal OS Backend")


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return _rate_limit_exceeded_handler(request, exc)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
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
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(categories_router)
app.include_router(contexts_router)
app.include_router(tags_router)
app.include_router(tasks_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )
