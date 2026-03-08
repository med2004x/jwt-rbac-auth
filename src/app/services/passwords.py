import base64
import hashlib
import hmac
import secrets


class PasswordService:
    _iterations = 600_000

    def hash_password(self, plain_secret: str) -> str:
        salt_bytes = secrets.token_bytes(16)
        derived_key = hashlib.pbkdf2_hmac("sha256", plain_secret.encode("utf-8"), salt_bytes, self._iterations)
        salt_text = base64.b64encode(salt_bytes).decode("ascii")
        hash_text = base64.b64encode(derived_key).decode("ascii")
        return f"pbkdf2_sha256${self._iterations}${salt_text}${hash_text}"

    def verify_password(self, plain_secret: str, password_hash: str) -> bool:
        algorithm_name, iteration_text, salt_text, hash_text = password_hash.split("$", 3)
        if algorithm_name != "pbkdf2_sha256":
            return False
        salt_bytes = base64.b64decode(salt_text.encode("ascii"))
        expected_key = base64.b64decode(hash_text.encode("ascii"))
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_secret.encode("utf-8"),
            salt_bytes,
            int(iteration_text),
        )
        return hmac.compare_digest(derived_key, expected_key)
