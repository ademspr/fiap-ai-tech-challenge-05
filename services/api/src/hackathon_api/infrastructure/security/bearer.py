import hashlib
import hmac
import secrets


def hash_bearer_token(plain: str) -> str:
    return "sha256:" + hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_bearer_token(plain: str, token_hash: str) -> bool:
    try:
        return hmac.compare_digest(hash_bearer_token(plain), token_hash)
    except (ValueError, TypeError):
        return False


def generate_bearer_token() -> str:
    return secrets.token_urlsafe(32)


def token_prefix(plain: str, length: int = 8) -> str:
    return plain[:length] if len(plain) >= length else plain
