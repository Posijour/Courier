from app.models import UserRecord
from app.services.supabase import supabase


async def get_or_create_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    *,
    last_name: str | None = None,
    language_code: str | None = None,
) -> UserRecord:
    row = await supabase.insert(
        "users",
        {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code or "ru",
        },
        params={"on_conflict": "telegram_id"},
        upsert=True,
    )
    if row is None:
        raise RuntimeError("Failed to upsert user")
    return UserRecord.from_dict(row)


async def get_user_by_telegram_id(telegram_id: int) -> UserRecord | None:
    row = await supabase.select(
        "users",
        {
            "select": "*",
            "telegram_id": f"eq.{telegram_id}",
            "limit": "1",
        },
        single=True,
    )
    return UserRecord.from_dict(row) if row else None
