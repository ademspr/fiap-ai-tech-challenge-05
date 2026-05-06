import re

_UUID_IN_PATH = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def split_path_group_and_endpoint(path: str) -> tuple[str, str]:
    """First URL path segment (path_group) and a template path (UUIDs -> {id}) for metrics."""
    raw = (path or "/").split("?")[0] or "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    endpoint = _UUID_IN_PATH.sub("{id}", raw) or "/"
    parts = [p for p in raw.split("/") if p]
    path_group = parts[0] if parts else "root"
    return path_group, endpoint
