from datetime import datetime, timezone

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Format as a fixed-width UTC string so it sorts correctly as text in SQLite."""
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)
