from hackathon_api.infrastructure.security.bearer import (
    generate_bearer_token,
    hash_bearer_token,
    token_prefix,
    verify_bearer_token,
)


def test_bearer_roundtrip():
    plain = generate_bearer_token()
    h = hash_bearer_token(plain)
    assert verify_bearer_token(plain, h)
    assert not verify_bearer_token(plain + "x", h)


def test_token_prefix_length():
    plain = "abcdefghijklmnop"
    assert token_prefix(plain, 8) == "abcdefgh"
