"""S3/MinIO object key layout shared by API and worker (relative DB paths unchanged)."""


def uploads_key(relative_path: str) -> str:
    p = relative_path.lstrip("/")
    return f"uploads/{p}"


def reports_key(relative_path: str) -> str:
    p = relative_path.lstrip("/")
    return f"reports/{p}"
