"""Request validation. Each function returns cleaned data or raises ValidationError."""
import re
from datetime import datetime, timezone

from .errors import ValidationError
from .timeutil import to_iso, utcnow

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 10


def _fail(errors):
    raise ValidationError("Validation failed.", details=errors)


def _require_object(payload):
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")


def _clean_string(payload, field, errors, required, max_len):
    value = payload.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[field] = f"{field} is required."
        return None
    if not isinstance(value, str):
        errors[field] = f"{field} must be a string."
        return None
    value = value.strip()
    if len(value) > max_len:
        errors[field] = f"{field} must be at most {max_len} characters."
        return None
    return value


def _parse_datetime(value):
    try:
        dt = datetime.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:  # naive values are treated as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_event_payload(payload, now=None):
    _require_object(payload)
    now = now or utcnow()
    errors = {}

    title = _clean_string(payload, "title", errors, True, 200)
    description = _clean_string(payload, "description", errors, False, 5000)
    location = _clean_string(payload, "location", errors, True, 200)

    date_iso = None
    raw_date = payload.get("date")
    if raw_date is None or raw_date == "":
        errors["date"] = "date is required."
    else:
        dt = _parse_datetime(raw_date) if isinstance(raw_date, str) else None
        if dt is None:
            errors["date"] = "date must be a valid ISO 8601 datetime (e.g. 2030-01-15T18:00:00Z)."
        elif dt <= now:
            errors["date"] = "date must be in the future."
        else:
            date_iso = to_iso(dt)

    capacity = payload.get("capacity")
    if capacity is None:
        errors["capacity"] = "capacity is required."
    elif isinstance(capacity, bool) or not isinstance(capacity, int):
        errors["capacity"] = "capacity must be an integer."
    elif capacity <= 0:
        errors["capacity"] = "capacity must be a positive integer."

    if errors:
        _fail(errors)
    return {
        "title": title,
        "description": description,
        "date": date_iso,
        "capacity": capacity,
        "location": location,
    }


def validate_registration_payload(payload):
    _require_object(payload)
    errors = {}

    name = _clean_string(payload, "name", errors, True, 100)
    email = _clean_string(payload, "email", errors, True, 254)
    if email is not None:
        if EMAIL_RE.match(email):
            email = email.lower()
        else:
            errors["email"] = "email must be a valid email address."

    if errors:
        _fail(errors)
    return {"name": name, "email": email}


def _positive_int(args, key, default, maximum=None):
    raw = args.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError("Validation failed.", details={key: f"{key} must be an integer."})
    if value < 1 or (maximum and value > maximum):
        limit = f"between 1 and {maximum}" if maximum else "at least 1"
        raise ValidationError("Validation failed.", details={key: f"{key} must be {limit}."})
    return value


def parse_event_query(args):
    when = args.get("when")
    if when is not None and when not in ("upcoming", "past"):
        raise ValidationError(
            "Validation failed.", details={"when": "when must be 'upcoming' or 'past'."}
        )
    location = (args.get("location") or "").strip() or None
    return {
        "page": _positive_int(args, "page", 1),
        "limit": _positive_int(args, "limit", DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "when": when,
        "location": location,
    }


def parse_registration_status(args):
    status = args.get("status")
    if status is not None:
        status = status.upper()
        if status not in ("CONFIRMED", "CANCELLED"):
            raise ValidationError(
                "Validation failed.",
                details={"status": "status must be CONFIRMED or CANCELLED."},
            )
    return status
