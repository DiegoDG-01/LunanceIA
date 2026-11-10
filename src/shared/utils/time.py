from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """MySQL (y SQLite) devuelven DATETIME sin zona: todas las fechas del proyecto son UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
