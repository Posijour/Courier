from aiogram import F, Router
from aiogram.types import Message

from app.keyboards.main import main_menu_keyboard
from app.services.accounts import resolve_tenant_context_for_telegram_user
from app.services.shifts import get_active_shift
from app.services.stats import (
    build_personal_stats_text,
    build_today_vs_yesterday_text,
    build_weekly_stats_text,
)
from app.utils.shift_status import format_shift_status_text

router = Router()


@router.message(F.text == "Моя статистика")
async def handle_my_stats(message: Message) -> None:
    if not message.from_user:
        return

    shift = await get_active_shift(message.from_user.id)
    text = await build_personal_stats_text(message.from_user.id)
    if shift:
        context = await resolve_tenant_context_for_telegram_user(message.from_user)
        text = "\n\n".join(
            [
                format_shift_status_text(
                    shift,
                    context.bot_settings.timezone,
                    title="Смена сейчас активна ✅",
                    orders_label="Заказов",
                    blank_after_title=False,
                ),
                text,
            ]
        )
    await message.answer(text, reply_markup=main_menu_keyboard(active_shift=shift is not None))


@router.message(F.text == "Сегодня vs вчера")
async def handle_today_vs_yesterday(message: Message) -> None:
    if not message.from_user:
        return

    shift = await get_active_shift(message.from_user.id)
    text = await build_today_vs_yesterday_text(message.from_user.id)
    await message.answer(text, reply_markup=main_menu_keyboard(active_shift=shift is not None))


@router.message(F.text == "Неделя")
async def handle_weekly_stats(message: Message) -> None:
    if not message.from_user:
        return

    shift = await get_active_shift(message.from_user.id)
    text = await build_weekly_stats_text(message.from_user.id)
    await message.answer(text, reply_markup=main_menu_keyboard(active_shift=shift is not None))
