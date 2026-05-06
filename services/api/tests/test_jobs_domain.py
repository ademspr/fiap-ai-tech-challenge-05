from hackathon_api.domain.policies import ALLOWED_CONTENT_TYPES


def test_allowed_mime_types():
    assert "image/png" in ALLOWED_CONTENT_TYPES
    assert "application/pdf" in ALLOWED_CONTENT_TYPES
