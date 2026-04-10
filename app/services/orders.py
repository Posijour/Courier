from decimal import Decimal

from app.models import OrderRecord
from app.services.accounts import resolve_tenant_context
from app.services.supabase import SupabaseError, supabase


async def create_order(
    telegram_id: int,
    source_mode: str,
    district: str | None = None,
    position_district: str | None = None,
    pickup_district: str | None = None,
    dropoff_district: str | None = None,
    platform: str | None = None,
    order_earnings: Decimal | None = None,
    external_order_id: str | None = None,
    zone_id: str | None = None,
    service_type_id: str | None = None,
    source: str | None = None,
    notes: str | None = None,
) -> OrderRecord:
    context = await resolve_tenant_context(telegram_id)
    try:
        row = await supabase.rpc(
            "create_order_for_account_user",
            {
                "p_account_id": context.account_id,
                "p_telegram_id": telegram_id,
                "p_source_mode": source_mode,
                "p_external_order_id": external_order_id,
                "p_currency": context.bot_settings.currency,
                "p_zone_id": zone_id,
                "p_service_type_id": service_type_id,
                "p_source": source,
                "p_district": district,
                "p_position_district": position_district,
                "p_pickup_district": pickup_district,
                "p_dropoff_district": dropoff_district,
                "p_platform": platform,
                "p_amount": float(order_earnings) if order_earnings is not None else None,
                "p_notes": notes,
            },
        )
    except SupabaseError as exc:
        if "User not found" in str(exc):
            raise ValueError("User not found") from exc
        raise

    if not row:
        raise RuntimeError("Failed to create order")
    payload = row[0] if isinstance(row, list) else row
    return OrderRecord.from_dict(payload)
