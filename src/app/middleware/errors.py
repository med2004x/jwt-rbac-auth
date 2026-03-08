from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from fastapi import Request, Response
from fastapi.responses import JSONResponse


async def error_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        request.app.state.logger.exception("request_failed", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
