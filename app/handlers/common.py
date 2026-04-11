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
    await message.answer("Используй кнопки внизу экрана 👇", reply_markup=main_menu_keyboard(active_shift=shift is not None))


@router.message(
    lambda message: bool(message.text)
    and message.text.startswith("/")
    and not message.text.split(maxsplit=1)[0].startswith("/start")
)
async def handle_menu_command_stub(message: Message) -> None:
    await message.answer("Используй кнопки ниже 👇")
