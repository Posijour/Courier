from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.utils.formatters import parse_iso_datetime


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


@dataclass(slots=True)
class UserRecord:
    id: str
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    phone: str | None
    language_code: str
    is_global_admin: bool
    legacy_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UserRecord":
        return cls(
            id=str(payload["id"]),
            telegram_id=int(payload["telegram_id"]),
            username=payload.get("username"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            phone=payload.get("phone"),
            language_code=payload.get("language_code", "ru"),
            is_global_admin=bool(payload.get("is_global_admin", False)),
            legacy_id=int(payload["legacy_id"]) if payload.get("legacy_id") is not None else None,
            created_at=parse_iso_datetime(payload.get("created_at")),
            updated_at=parse_iso_datetime(payload.get("updated_at")),
        )


@dataclass(slots=True)
class ShiftRecord:
    id: int
    account_id: str
    user_id: str
    mode: str
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
    orders_count: int
    earnings_total: Decimal | None
    city: str | None
    weather_summary: str | None
    weather_temp: Decimal | None
    weather_rain: bool | None
    status: str
    notes: str | None
    legacy_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ShiftRecord":
        return cls(
            id=int(payload["id"]),
            account_id=str(payload["account_id"]),
            user_id=str(payload["user_id"]),
            mode=payload.get("mode", "basic"),
            started_at=parse_iso_datetime(payload["started_at"]) or datetime.utcnow(),
            ended_at=parse_iso_datetime(payload.get("ended_at")),
            duration_minutes=payload.get("duration_minutes"),
            orders_count=int(payload.get("orders_count", 0)),
            earnings_total=_to_decimal(payload.get("earnings_total")),
            city=payload.get("city"),
            weather_summary=payload.get("weather_summary"),
            weather_temp=_to_decimal(payload.get("weather_temp")),
            weather_rain=payload.get("weather_rain"),
            status=payload.get("status", "active"),
            notes=payload.get("notes"),
            legacy_user_id=int(payload["legacy_user_id"]) if payload.get("legacy_user_id") is not None else None,
            created_at=parse_iso_datetime(payload.get("created_at")),
            updated_at=parse_iso_datetime(payload.get("updated_at")),
        )


@dataclass(slots=True)
class OrderRecord:
    id: int
    account_id: str
    user_id: str
    shift_id: int | None
    source_mode: str
    amount: Decimal
    currency: str
    status: str
    ordered_at: datetime | None = None
    external_order_id: str | None = None
    zone_id: str | None = None
    service_type_id: str | None = None
    source: str | None = None
    district: str | None = None
    position_district: str | None = None
    pickup_district: str | None = None
    dropoff_district: str | None = None
    platform: str | None = None
    notes: str | None = None
    legacy_user_id: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OrderRecord":
        return cls(
            id=int(payload["id"]),
            account_id=str(payload["account_id"]),
            user_id=str(payload["user_id"]),
            shift_id=int(payload["shift_id"]) if payload.get("shift_id") is not None else None,
            source_mode=payload["source_mode"],
            amount=_to_decimal(payload.get("amount")) or Decimal("0"),
            currency=payload.get("currency", "RSD"),
            status=payload.get("status", "completed"),
            ordered_at=parse_iso_datetime(payload.get("ordered_at")),
            external_order_id=payload.get("external_order_id"),
            zone_id=str(payload["zone_id"]) if payload.get("zone_id") is not None else None,
            service_type_id=str(payload["service_type_id"]) if payload.get("service_type_id") is not None else None,
            source=payload.get("source"),
            district=payload.get("district"),
            position_district=payload.get("position_district"),
            pickup_district=payload.get("pickup_district"),
            dropoff_district=payload.get("dropoff_district"),
            platform=payload.get("platform"),
            notes=payload.get("notes"),
            legacy_user_id=int(payload["legacy_user_id"]) if payload.get("legacy_user_id") is not None else None,
        )


@dataclass(slots=True)
class PersonalStats:
    shifts_count: int
    orders_count: int
    total_earnings: Decimal
    avg_eph: Decimal

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PersonalStats":
        return cls(
            shifts_count=int(payload.get("shifts_count", 0)),
            orders_count=int(payload.get("orders_count", 0)),
            total_earnings=_to_decimal(payload.get("total_earnings")) or Decimal("0"),
            avg_eph=_to_decimal(payload.get("avg_eph")) or Decimal("0"),
        )


@dataclass(slots=True)
class AccountRecord:
    id: str
    name: str
    slug: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AccountRecord":
        return cls(
            id=str(payload["id"]),
            name=payload["name"],
            slug=payload["slug"],
            status=payload.get("status", "active"),
            created_at=parse_iso_datetime(payload.get("created_at")),
            updated_at=parse_iso_datetime(payload.get("updated_at")),
        )


@dataclass(slots=True)
class AccountUserRecord:
    id: str
    account_id: str
    user_id: str
    role: str
    is_active: bool
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AccountUserRecord":
        return cls(
            id=str(payload["id"]),
            account_id=str(payload["account_id"]),
            user_id=str(payload["user_id"]),
            role=payload.get("role", "worker"),
            is_active=bool(payload.get("is_active", True)),
            created_at=parse_iso_datetime(payload.get("created_at")),
        )


@dataclass(slots=True)
class BotSettingsRecord:
    id: str
    account_id: str
    timezone: str
    currency: str
    locale: str
    shift_tracking_enabled: bool
    zones_enabled: bool
    service_types_enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BotSettingsRecord":
        return cls(
            id=str(payload["id"]),
            account_id=str(payload["account_id"]),
            timezone=payload.get("timezone", "Europe/Belgrade"),
            currency=payload.get("currency", "RSD"),
            locale=payload.get("locale", "ru"),
            shift_tracking_enabled=bool(payload.get("shift_tracking_enabled", True)),
            zones_enabled=bool(payload.get("zones_enabled", True)),
            service_types_enabled=bool(payload.get("service_types_enabled", False)),
            created_at=parse_iso_datetime(payload.get("created_at")),
            updated_at=parse_iso_datetime(payload.get("updated_at")),
        )


@dataclass(slots=True)
class TenantContext:
    user: UserRecord
    membership: AccountUserRecord
    account: AccountRecord
    bot_settings: BotSettingsRecord

    @property
    def account_id(self) -> str:
        return self.account.id
