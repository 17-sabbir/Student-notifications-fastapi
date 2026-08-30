from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BD_TZ = ZoneInfo("Asia/Dhaka")
UTC_TZ = timezone.utc


def utc_now() -> datetime:
    """Current UTC time as a naive datetime.

    The database stores naive UTC (timestamp without time zone), so all
    persistence uses this. Replaces the deprecated datetime.utcnow().
    """
    return datetime.now(UTC_TZ).replace(tzinfo=None)


def to_bd_isoformat(dt: datetime | None) -> str | None:
    """Convert a stored naive UTC datetime to Bangladesh-time ISO 8601.

    Returns e.g. '2026-08-30T06:34:00+06:00' so clients can render local
    (Bangladesh) time correctly. None passes through as None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(BD_TZ).isoformat()
