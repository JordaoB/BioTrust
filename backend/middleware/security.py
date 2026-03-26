from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Deque, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers for production hardening."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "font-src 'self' data: https://cdnjs.cloudflare.com; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per IP."""

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = timedelta(minutes=1)
        self._requests: Dict[str, Deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        path = request.url.path

        # Liveness frame streaming naturally produces many requests per minute.
        # Give this endpoint a higher cap to avoid blocking the full session.
        if path.startswith("/api/liveness-stream/frame/"):
            limit = max(self.requests_per_minute, 1800)
        else:
            limit = self.requests_per_minute

        bucket = "liveness_frame" if path.startswith("/api/liveness-stream/frame/") else "default"
        key = f"{client_ip}:{bucket}"

        with self._lock:
            queue = self._requests[key]
            cutoff = now - self.window
            while queue and queue[0] < cutoff:
                queue.popleft()

            if len(queue) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "limit": limit,
                        "window_seconds": 60,
                    },
                )

            queue.append(now)

        return await call_next(request)
