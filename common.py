from datetime import datetime, timezone
from uuid import uuid4

STATUSES = {"todo", "in_progress", "done"}

def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def new_id():
    return str(uuid4())

def validate(payload, allowed, required=()):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    extra = set(payload) - set(allowed)
    if extra:
        raise ValueError("Unknown field(s): " + ", ".join(sorted(extra)))
    for field in required:
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")
    for field in ("name", "title"):
        if field in payload and (not isinstance(payload[field], str) or not payload[field].strip()):
            raise ValueError(f"{field} must be a nonempty string")
    for field in ("description",):
        if field in payload and not isinstance(payload[field], str):
            raise ValueError(f"{field} must be a string")
    if "status" in payload and payload["status"] not in STATUSES:
        raise ValueError("status must be todo, in_progress, or done")
    if "due_at" in payload and payload["due_at"] is not None:
        if not isinstance(payload["due_at"], str):
            raise ValueError("due_at must be an ISO-8601 date-time string or null")
        try:
            d = datetime.fromisoformat(payload["due_at"].replace("Z", "+00:00"))
            if d.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError("due_at must include a timezone (e.g. 2026-12-01T12:00:00Z)")
    return payload

PROJECT_FIELDS = ("name", "description")
TASK_FIELDS = ("title", "description", "status", "due_at")
