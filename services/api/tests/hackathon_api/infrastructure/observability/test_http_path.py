from hackathon_api.infrastructure.observability.http_path import split_path_group_and_endpoint


def test_split_root():
    g, e = split_path_group_and_endpoint("/")
    assert g == "root"
    assert e == "/"


def test_split_normalizes_uuid_to_placeholder():
    jid = "550e8400-e29b-41d4-a716-446655440000"
    g, e = split_path_group_and_endpoint(f"/v1/analysis-jobs/{jid}/report")
    assert g == "v1"
    assert e == "/v1/analysis-jobs/{id}/report"


def test_query_string_stripped():
    g, e = split_path_group_and_endpoint("/health?x=1")
    assert g == "health"
    assert e == "/health"
