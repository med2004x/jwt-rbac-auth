from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.services.tokens import TokenError, TokenService


async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    authorization_header = request.headers.get("authorization")
    if authorization_header and authorization_header.lower().startswith("bearer "):
        bearer_token = authorization_header.split(" ", 1)[1]
        token_service: TokenService = request.app.state.token_service
        try:
            request.state.token_subject = token_service.decode_access_token(bearer_token)
        except TokenError:
            request.state.token_subject = None
    else:
        request.state.token_subject = None
    return await call_next(request)

