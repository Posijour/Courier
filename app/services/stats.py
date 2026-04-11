from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings
from app.models import PersonalStats, ShiftRecord, TenantContext
from app.services.accounts import resolve_tenant_context
from app.services.supabase import supabase
from app.utils.formatters import format_hour_value, format_money_value


def _project_timezone(context: TenantContext) -> ZoneInfo:
    try:
        return ZoneInfo(context.bot_settings.timezone)
    except ZoneInfoNotFoundError:
        return settings.project_timezone


@dataclass(slots=True)
class AggregatedShiftStats:
    shifts_count: int = 0
    orders_count: int = 0
    total_earnings: Decimal = Decimal("0")
    total_hours: Decimal = Decimal("0")

    @property
    def avg_hourly(self) -> Decimal:
        if self.total_hours <= 0:
            return Decimal("0")
        return self.total_earnings / self.total_hours

    @property
    def has_data(self) -> bool:
        return self.shifts_count > 0


def _rpc_scalar(payload, key: str) -> Decimal | None:
    if payload is None:
        return None
    if isinstance(payload, list):
        if not payload:
            return None
        payload = payload[0]
    if isinstance(payload, dict):
        value = payload.get(key)
        return Decimal(str(value)) if value is not None else None
    return Decimal(str(payload))


def _to_project_datetime(value: datetime, context: TenantContext) -> datetime:
    project_timezone = _project_timezone(context)
    if value.tzinfo is None:
        return value.replace(tzinfo=project_timezone)
    return value.astimezone(project_timezone)


def _format_signed_money(value: Decimal, currency: str) -> str:
    rounded = Decimal(str(value)).quantize(Decimal("0.01"))
    sign = "+" if rounded >= 0 else "-"
    return f"{sign}{format_money_value(abs(rounded))} {currency}"


def _format_signed_int(value: int) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value)}"


def _format_signed_hourly(value: Decimal, currency: str) -> str:
    rounded = Decimal(str(value)).quantize(Decimal("0.1"))
    sign = "+" if rounded >= 0 else "-"
    return f"{sign}{format_hour_value(abs(rounded))} {currency}/ч"


def _format_stats_block(title: str, stats: AggregatedShiftStats, currency: str) -> list[str]:
    return [
        f"{title}:",
        f"Смен: {stats.shifts_count}",
        f"💰 {format_money_value(stats.total_earnings)} {currency}",
        f"📦 {stats.orders_count} заказов",
        f"Часов: {format_hour_value(stats.total_hours)}",
        f"{currency}/ч: {format_hour_value(stats.avg_hourly)}",
    ]


def _aggregate_shifts(shifts: list[ShiftRecord]) -> AggregatedShiftStats:
    stats = AggregatedShiftStats()
    for shift in shifts:
        stats.shifts_count += 1
        stats.orders_count += shift.orders_count
        stats.total_earnings += shift.earnings_total or Decimal("0")
        if shift.duration_minutes:
            stats.total_hours += Decimal(shift.duration_minutes) / Decimal("60")
    return stats


async def _get_completed_shifts_for_window(
    context: TenantContext,
    period_start: datetime,
    period_end: datetime,
) -> list[ShiftRecord]:
    rows = await supabase.select(
        "shifts",
        {
            "select": "*",
            "account_id": f"eq.{context.account_id}",
            "user_id": f"eq.{context.user.id}",
            "status": "eq.completed",
            "earnings_total": "not.is.null",
            "ended_at": f"gte.{period_start.isoformat()}",
            "order": "ended_at.asc",
        },
    )
    payload = rows or []
    shifts = [ShiftRecord.from_dict(row) for row in payload if row.get("ended_at")]
    return [
        shift
        for shift in shifts
        if shift.ended_at is not None and _to_project_datetime(shift.ended_at, context) < period_end
    ]


def _day_income_label(day_value: date) -> str:
    return day_value.strftime("%d.%m")


async def average_earnings_per_hour_before_shift(account_id: str, user_id: str, current_shift_id: int) -> Decimal | None:
    value = await supabase.rpc(
        "average_earnings_per_hour_before_shift",
        {
            "p_account_id": account_id,
            "p_user_id": user_id,
            "p_shift_id": current_shift_id,
        },
    )
    return _rpc_scalar(value, "average_earnings_per_hour_before_shift")


async def build_personal_stats_text(telegram_id: int) -> str:
    context = await resolve_tenant_context(telegram_id)
    payload = await supabase.rpc(
        "get_personal_stats",
        {
            "p_account_id": context.account_id,
            "p_user_id": context.user.id,
        },
    )
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    stats = PersonalStats.from_dict(payload or {})
    currency = context.bot_settings.currency

    return "\n".join(
        [
            "Моя статистика:",
            f"Смен: {stats.shifts_count}",
            f"Заказов: {stats.orders_count}",
            f"💰 {format_money_value(stats.total_earnings)} {currency}",
            f"{format_money_value(stats.avg_eph)} {currency}/час",
        ]
    )


async def build_today_vs_yesterday_text(telegram_id: int) -> str:
    context = await resolve_tenant_context(telegram_id)
    currency = context.bot_settings.currency
    now = datetime.now(_project_timezone(context))
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    shifts = await _get_completed_shifts_for_window(context, yesterday_start, now)

    today_shifts = [
        shift
        for shift in shifts
        if shift.ended_at is not None and _to_project_datetime(shift.ended_at, context) >= today_start
    ]
    yesterday_shifts = [
        shift
        for shift in shifts
        if shift.ended_at is not None and yesterday_start <= _to_project_datetime(shift.ended_at, context) < today_start
    ]

    today_stats = _aggregate_shifts(today_shifts)
    yesterday_stats = _aggregate_shifts(yesterday_shifts)

    if not today_stats.has_data and not yesterday_stats.has_data:
        return "Сегодня vs вчера\n\nНедостаточно данных для сравнения сегодня и вчера."

    lines = ["Сегодня vs вчера", ""]
    if today_stats.has_data:
        lines.extend(_format_stats_block("Сегодня", today_stats, currency))
    else:
        lines.append("За сегодня пока нет завершенных смен.")

    lines.append("")

    if yesterday_stats.has_data:
        lines.extend(_format_stats_block("Вчера", yesterday_stats, currency))
    else:
        lines.append("За вчера пока нет завершенных смен.")

    if today_stats.has_data and yesterday_stats.has_data:
        income_delta = today_stats.total_earnings - yesterday_stats.total_earnings
        orders_delta = today_stats.orders_count - yesterday_stats.orders_count
        hourly_delta = today_stats.avg_hourly - yesterday_stats.avg_hourly
        lines.extend(
            [
                "",
                "Разница:",
                f"Доход: {_format_signed_money(income_delta, currency)}",
                f"Заказы: {_format_signed_int(orders_delta)}",
                f"{currency}/ч: {_format_signed_hourly(hourly_delta, currency)}",
            ]
        )

    return "\n".join(lines)


async def build_weekly_stats_text(telegram_id: int) -> str:
    context = await resolve_tenant_context(telegram_id)
    currency = context.bot_settings.currency
    now = datetime.now(_project_timezone(context))
    period_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    shifts = await _get_completed_shifts_for_window(context, period_start, now)
    stats = _aggregate_shifts(shifts)

    if not stats.has_data:
        return "Неделя\n\nЗа последние 7 дней пока нет завершенных смен."

    daily_income: dict[date, Decimal] = {}
    for shift in shifts:
        if shift.ended_at is None:
            continue
        local_day = _to_project_datetime(shift.ended_at, context).date()
        daily_income[local_day] = daily_income.get(local_day, Decimal("0")) + (shift.earnings_total or Decimal("0"))

    best_day = max(daily_income.items(), key=lambda item: (item[1], item[0]))
    worst_day = min(daily_income.items(), key=lambda item: (item[1], item[0]))

    lines = [
        "Неделя",
        "",
        f"Смен: {stats.shifts_count}",
        f"Заказов: {stats.orders_count}",
        f"Доход: {format_money_value(stats.total_earnings)} {currency}",
        f"Часов: {format_hour_value(stats.total_hours)}",
        f"{currency}/ч: {format_hour_value(stats.avg_hourly)}",
        "",
        f"Лучший день: {_day_income_label(best_day[0])} ({format_money_value(best_day[1])} {currency})",
        f"Худший день: {_day_income_label(worst_day[0])} ({format_money_value(worst_day[1])} {currency})",
    ]
    return "\n".join(lines)
