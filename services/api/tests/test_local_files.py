import hashlib
from uuid import UUID

from hackathon_api.infrastructure.storage.local_files import (
    diagram_relative_path,
    relative_report_path,
    sha256_hex,
)

_JOB_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_diagram_relative_path():
    assert diagram_relative_path(_JOB_ID, "photo.png") == f"{_JOB_ID}/photo.png"


def test_diagram_relative_path_strips_directory_traversal():
    assert diagram_relative_path(_JOB_ID, "../../etc/passwd") == f"{_JOB_ID}/passwd"


def test_relative_report_path():
    assert relative_report_path(_JOB_ID) == f"{_JOB_ID}.json"


def test_sha256_hex():
    data = b"hello"
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_hex(data) == expected


def test_sha256_hex_empty():
    assert sha256_hex(b"") == hashlib.sha256(b"").hexdigest()
