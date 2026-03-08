import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response


async def logging_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request_started_at = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
    request.app.state.logger.info(
        "request_handled",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
    )
    return response

