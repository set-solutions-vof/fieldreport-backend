from src.security.invite_tokens import hash_invite_token


def test_hash_invite_token_returns_stable_sha256_hex() -> None:
    assert hash_invite_token("raw-token") == hash_invite_token("raw-token")
    assert len(hash_invite_token("raw-token")) == 64
