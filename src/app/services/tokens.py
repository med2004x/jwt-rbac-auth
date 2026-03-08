from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenSubject:
    user_id: int
    email: str
    role: str


class TokenService:
    def __init__(
        self,
        secret_key: str,
        issuer: str,
        audience: str,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ) -> None:
        self._secret_key = secret_key
        self._issuer = issuer
        self._audience = audience
        self.access_ttl_seconds = access_ttl_seconds
        self.refresh_ttl_seconds = refresh_ttl_seconds

    def issue_access_token(self, token_subject: TokenSubject) -> str:
        expires_at = datetime.now(tz=UTC) + timedelta(seconds=self.access_ttl_seconds)
        return jwt.encode(
            {
                "sub": str(token_subject.user_id),
                "email": token_subject.email,
                "role": token_subject.role,
                "aud": self._audience,
                "iss": self._issuer,
                "exp": expires_at,
                "token_use": "access",
            },
            self._secret_key,
            algorithm="HS256",
        )

    def issue_refresh_token(self, token_subject: TokenSubject) -> tuple[str, str]:
        token_identifier = str(uuid4())
        expires_at = datetime.now(tz=UTC) + timedelta(seconds=self.refresh_ttl_seconds)
        encoded_token = jwt.encode(
            {
                "sub": str(token_subject.user_id),
                "email": token_subject.email,
                "role": token_subject.role,
                "jti": token_identifier,
                "aud": self._audience,
                "iss": self._issuer,
                "exp": expires_at,
                "token_use": "refresh",
            },
            self._secret_key,
            algorithm="HS256",
        )
        return encoded_token, token_identifier

    def decode_access_token(self, encoded_token: str) -> TokenSubject:
        decoded_payload = self._decode(encoded_token, expected_use="access")
        return TokenSubject(
            user_id=int(decoded_payload["sub"]),
            email=decoded_payload["email"],
            role=decoded_payload["role"],
        )

    def decode_refresh_token(self, encoded_token: str) -> tuple[TokenSubject, str]:
        decoded_payload = self._decode(encoded_token, expected_use="refresh")
        return (
            TokenSubject(
                user_id=int(decoded_payload["sub"]),
                email=decoded_payload["email"],
                role=decoded_payload["role"],
            ),
            decoded_payload["jti"],
        )

    def _decode(self, encoded_token: str, expected_use: str) -> dict[str, str]:
        try:
            decoded_payload = jwt.decode(
                encoded_token,
                self._secret_key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except jwt.PyJWTError as exc:
            raise TokenError("Token validation failed") from exc
        if decoded_payload.get("token_use") != expected_use:
            raise TokenError("Unexpected token type")
        return decoded_payload

