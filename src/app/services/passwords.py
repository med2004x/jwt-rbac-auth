from passlib.context import CryptContext


class PasswordService:
    def __init__(self) -> None:
        self._context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, plain_secret: str) -> str:
        return self._context.hash(plain_secret)

    def verify_password(self, plain_secret: str, password_hash: str) -> bool:
        return self._context.verify(plain_secret, password_hash)

