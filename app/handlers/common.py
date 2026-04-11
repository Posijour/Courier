from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards.main import main_menu_keyboard
from app.services.accounts import resolve_tenant_context_for_telegram_user
from app.services.shifts import get_active_shift

router = Router()


@router.message(Command("start"))
@router.message(Command("help"))
@router.message(Command("shift_start"))
@router.message(Command("shift_end"))
@router.message(Command("order_add"))
@router.message(Command("stats"))
async def handle_menu_commands_stub(message: Message) -> None:
    if not message.from_user:
        return

    await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await get_active_shift(message.from_user.id)
    await message.answer("Koristi dugmad ispod 👇", reply_markup=main_menu_keyboard(active_shift=shift is not None))


@router.message(lambda message: bool(message.text) and message.text.startswith("/"))
async def handle_menu_command_stub(message: Message) -> None:
    await message.answer("Koristi dugmad ispod 👇")
