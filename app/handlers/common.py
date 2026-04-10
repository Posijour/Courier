from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.main import main_menu_keyboard
from app.services.accounts import resolve_tenant_context_for_telegram_user
from app.services.shifts import get_active_shift

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if not message.from_user:
        return

    await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await get_active_shift(message.from_user.id)
    await message.answer("Меню", reply_markup=main_menu_keyboard(active_shift=shift is not None))
