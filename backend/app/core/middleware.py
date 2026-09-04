from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.security import generate_csrf_token

settings = get_settings()

Handler = Callable[[Request], Awaitable[Response]]


class CSRFCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        response = await call_next(request)
        if settings.csrf_cookie_name not in request.cookies:
            response.set_cookie(
                key=settings.csrf_cookie_name,
                value=generate_csrf_token(),
                httponly=False,
                secure=settings.cookie_secure,
                samesite="lax",
                path="/",
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
