from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_decimal(raw_value: str) -> Decimal | None:
    normalized = raw_value.strip().replace(",", ".").replace(" ", "")
    if not normalized:
        return None
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None
    if value < 0:
        return None
    return value.quantize(Decimal("0.01"))


def format_money_value(value) -> str:
    decimal_value = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    if decimal_value == decimal_value.to_integral():
        return str(int(decimal_value))
    return format(decimal_value.normalize(), "f")


def format_hour_value(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.1"))
    if rounded == rounded.to_integral():
        return str(int(rounded))
    return format(rounded.normalize(), "f")


def format_percent_delta(value: Decimal) -> str:
    rounded = abs(value).quantize(Decimal("0.1"))
    if rounded == rounded.to_integral():
        number = str(int(rounded))
    else:
        number = format(rounded.normalize(), "f")
    sign = "+" if value >= 0 else ""
    return f"{sign}{number}%"


def parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
