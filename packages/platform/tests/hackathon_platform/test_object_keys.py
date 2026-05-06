from hackathon_platform.object_keys import reports_key, uploads_key


def test_uploads_key_strips_leading_slash():
    assert uploads_key("/a/b") == "uploads/a/b"


def test_reports_key():
    assert reports_key("job.json") == "reports/job.json"
