from datetime import datetime, timezone
from decimal import Decimal

from aiogram.types import User as TelegramUser

from app.config import settings
from app.models import ShiftRecord, TenantContext
from app.services.accounts import resolve_tenant_context, resolve_tenant_context_for_telegram_user
from app.services.stats import average_earnings_per_hour_before_shift
from app.services.supabase import SupabaseError, supabase
from app.services.weather import fetch_weather_snapshot_for_timezone
from app.utils.formatters import format_hour_value, format_money_value, format_percent_delta


async def get_active_shift_for_context(context: TenantContext) -> ShiftRecord | None:
    row = await supabase.select(
        "shifts",
        {
            "select": "*",
            "account_id": f"eq.{context.account_id}",
            "user_id": f"eq.{context.user.id}",
            "status": "eq.active",
            "order": "started_at.desc",
            "limit": "1",
        },
        single=True,
    )
    return ShiftRecord.from_dict(row) if row else None


async def get_active_shift(telegram_id: int) -> ShiftRecord | None:
    context = await resolve_tenant_context(telegram_id)
    return await get_active_shift_for_context(context)


async def start_shift(tg_user: TelegramUser, mode: str = "basic") -> ShiftRecord:
    context = await resolve_tenant_context_for_telegram_user(tg_user)
    active_shift = await get_active_shift_for_context(context)
    if active_shift:
        return active_shift

    weather = await fetch_weather_snapshot_for_timezone(context.bot_settings.timezone)
    started_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "account_id": context.account_id,
        "user_id": context.user.id,
        "legacy_user_id": context.user.legacy_id,
        "started_at": started_at,
        "legacy_start_time": started_at,
        "city": settings.default_city,
        "weather_summary": weather.summary,
        "weather_temp": float(weather.temp) if weather.temp is not None else None,
        "weather_rain": weather.rain,
        "status": "active",
        "mode": mode,
    }
    try:
        row = await supabase.insert("shifts", payload)
    except SupabaseError as exc:
        if "uniq_active_shift_per_user_account" not in str(exc):
            raise
        existing = await get_active_shift_for_context(context)
        if existing is None:
            raise
        return existing

    if row is None:
        raise RuntimeError("Failed to create shift")
    return ShiftRecord.from_dict(row)


async def close_shift(telegram_id: int, earnings_total: Decimal) -> ShiftRecord | None:
    context = await resolve_tenant_context(telegram_id)
    row = await supabase.rpc(
        "close_active_shift",
        {
            "p_account_id": context.account_id,
            "p_telegram_id": telegram_id,
            "p_earnings_total": float(earnings_total),
        },
    )
    if not row:
        return None
    payload = row[0] if isinstance(row, list) else row
    return ShiftRecord.from_dict(payload)


async def close_shift_summary(shift: ShiftRecord) -> str:
    duration_hours = Decimal(shift.duration_minutes or 0) / Decimal("60")
    earnings_per_hour = (
        (Decimal(str(shift.earnings_total)) / duration_hours).quantize(Decimal("0.01"))
        if duration_hours > 0 and shift.earnings_total is not None
        else Decimal("0")
    )
    historical_avg = await average_earnings_per_hour_before_shift(shift.account_id, shift.user_id, shift.id)
    currency = await _get_currency_for_account(shift.account_id)

    lines = [
        "Danas:",
        f"{format_hour_value(duration_hours)}h",
        f"💰 {format_money_value(shift.earnings_total)} {currency}",
        f"📦 Porudžbina: {shift.orders_count}",
        "",
        f"{format_money_value(earnings_per_hour)} {currency}/h",
    ]

    if historical_avg is not None and historical_avg > 0:
        delta = ((earnings_per_hour - historical_avg) / historical_avg) * Decimal("100")
        direction = "više" if delta >= 0 else "niže"
        lines.append(f"{direction} od tvog proseka ({format_percent_delta(delta)})")

    return "\n".join(lines)


async def _get_currency_for_account(account_id: str) -> str:
    row = await supabase.select(
        "bot_settings",
        {
            "select": "currency",
            "account_id": f"eq.{account_id}",
            "limit": "1",
        },
        single=True,
    )
    return row.get("currency", "RSD") if row else "RSD"
