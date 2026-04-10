from aiogram.types import User as TelegramUser

from app.config import settings
from app.models import (
    AccountRecord,
    AccountUserRecord,
    BotSettingsRecord,
    TenantContext,
    UserRecord,
)
from app.services.supabase import supabase
from app.services.users import get_or_create_user, get_user_by_telegram_id


class AccountResolutionError(RuntimeError):
    pass


def _membership_order_key(membership: AccountUserRecord) -> tuple[int, str]:
    role_rank = {"owner": 0, "manager": 1, "worker": 2}
    return (role_rank.get(membership.role, 99), membership.created_at.isoformat() if membership.created_at else "")


async def _get_account(account_id: str) -> AccountRecord:
    row = await supabase.select(
        "accounts",
        {
            "select": "*",
            "id": f"eq.{account_id}",
            "limit": "1",
        },
        single=True,
    )
    if row is None:
        raise AccountResolutionError("Account not found")
    return AccountRecord.from_dict(row)


async def _get_bot_settings(account_id: str) -> BotSettingsRecord:
    row = await supabase.select(
        "bot_settings",
        {
            "select": "*",
            "account_id": f"eq.{account_id}",
            "limit": "1",
        },
        single=True,
    )
    if row is None:
        raise AccountResolutionError("Bot settings not found for account")
    return BotSettingsRecord.from_dict(row)


async def _list_active_memberships(user_id: str) -> list[AccountUserRecord]:
    rows = await supabase.select(
        "account_users",
        {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "is_active": "eq.true",
            "order": "created_at.asc",
        },
    )
    return [AccountUserRecord.from_dict(row) for row in (rows or [])]


async def _ensure_default_membership(user: UserRecord) -> None:
    account = await supabase.select(
        "accounts",
        {
            "select": "*",
            "slug": f"eq.{settings.default_account_slug}",
            "limit": "1",
        },
        single=True,
    )
    if account is None:
        raise AccountResolutionError(
            f"Default account '{settings.default_account_slug}' not found. Run the multi-tenant migration first."
        )

    await supabase.insert(
        "account_users",
        {
            "account_id": account["id"],
            "user_id": user.id,
            "role": "worker",
            "is_active": True,
        },
        params={"on_conflict": "account_id,user_id"},
        upsert=True,
    )


async def resolve_tenant_context_by_user(user: UserRecord) -> TenantContext:
    memberships = await _list_active_memberships(user.id)
    if not memberships:
        await _ensure_default_membership(user)
        memberships = await _list_active_memberships(user.id)

    if not memberships:
        raise AccountResolutionError("User has no active account memberships")

    if len(memberships) > 1:
        unique_accounts = {membership.account_id for membership in memberships}
        if len(unique_accounts) > 1:
            raise AccountResolutionError("Multiple active accounts are not supported yet for V1")

    membership = sorted(memberships, key=_membership_order_key)[0]
    account = await _get_account(membership.account_id)
    if account.status != "active":
        raise AccountResolutionError("Account is not active")
    bot_settings = await _get_bot_settings(account.id)
    return TenantContext(
        user=user,
        membership=membership,
        account=account,
        bot_settings=bot_settings,
    )


async def resolve_tenant_context(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> TenantContext:
    user = await get_user_by_telegram_id(telegram_id)
    if user is None:
        user = await get_or_create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
    return await resolve_tenant_context_by_user(user)


async def resolve_tenant_context_for_telegram_user(tg_user: TelegramUser) -> TenantContext:
    return await resolve_tenant_context(
        tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language_code=tg_user.language_code,
    )


def supports_advanced_mode(context: TenantContext) -> bool:
    return context.membership.role in {"owner", "manager"}
