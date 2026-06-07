import hashlib


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
