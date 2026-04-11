from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings
from app.models import ShiftRecord


def _to_timezone(value: datetime, timezone_name: str) -> datetime:
    try:
        target_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        target_timezone = settings.project_timezone

    if value.tzinfo is None:
        return value.replace(tzinfo=target_timezone)
    return value.astimezone(target_timezone)


def format_shift_start_time(shift: ShiftRecord, timezone_name: str) -> str:
    return _to_timezone(shift.started_at, timezone_name).strftime("%H:%M")


def format_shift_status_text(
    shift: ShiftRecord,
    timezone_name: str,
    title: str = "Смена активна ✅",
    orders_label: str = "Заказов",
    blank_after_title: bool = True,
) -> str:
    start_time = format_shift_start_time(shift, timezone_name)
    separator = "\n\n" if blank_after_title else "\n"
    return f"{title} {separator}Старт: {start_time}\n{orders_label}: {shift.orders_count}"
