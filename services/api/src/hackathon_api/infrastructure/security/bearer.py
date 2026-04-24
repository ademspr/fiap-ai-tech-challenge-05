import secrets

import bcrypt


def hash_bearer_token(plain: str) -> str:
    digest = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return digest.decode("utf-8")


def verify_bearer_token(plain: str, token_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), token_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_bearer_token() -> str:
    return secrets.token_urlsafe(32)


def token_prefix(plain: str, length: int = 8) -> str:
    return plain[:length] if len(plain) >= length else plain
