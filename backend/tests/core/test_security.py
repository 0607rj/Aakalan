from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret")
    assert hashed.startswith("$argon2")
    assert verify_password("s3cret", hashed)
    assert not verify_password("nope", hashed)
    assert not verify_password("s3cret", "not-a-hash")


def test_token_roundtrip() -> None:
    payload = decode_access_token(create_access_token("u1", "o1", "viewer"))
    assert (payload["sub"], payload["org"], payload["role"]) == ("u1", "o1", "viewer")
