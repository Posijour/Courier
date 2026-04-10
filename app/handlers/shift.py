from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.keyboards.main import main_menu_keyboard
from app.services.accounts import resolve_tenant_context_for_telegram_user, supports_advanced_mode
from app.services.shifts import close_shift, close_shift_summary, get_active_shift, start_shift
from app.states import CloseShiftStates, StartShiftStates
from app.utils.formatters import parse_decimal
from app.utils.shift_status import format_shift_status_text

router = Router()


def _shift_mode_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Advanced"), KeyboardButton(text="Research")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "Старт смены")
async def handle_start_shift(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    shift = await get_active_shift(message.from_user.id)
    if shift:
        context = await resolve_tenant_context_for_telegram_user(message.from_user)
        await message.answer(
            format_shift_status_text(
                shift,
                context.bot_settings.timezone,
                title="Смена уже активна",
            ),
            reply_markup=main_menu_keyboard(active_shift=True),
        )
        return

    context = await resolve_tenant_context_for_telegram_user(message.from_user)
    if supports_advanced_mode(context):
        await state.set_state(StartShiftStates.waiting_for_mode)
        await message.answer("Выберите режим смены", reply_markup=_shift_mode_keyboard())
        return

    await state.clear()
    shift = await start_shift(message.from_user, mode="basic")
    await message.answer(
        format_shift_status_text(shift, context.bot_settings.timezone),
        reply_markup=main_menu_keyboard(active_shift=True),
    )


@router.message(StartShiftStates.waiting_for_mode)
async def handle_start_shift_mode(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return

    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu_keyboard())
        return

    if message.text not in {"Advanced", "Research"}:
        await message.answer("Выберите Advanced или Research", reply_markup=_shift_mode_keyboard())
        return

    shift = await get_active_shift(message.from_user.id)
    if shift:
        await state.clear()
        context = await resolve_tenant_context_for_telegram_user(message.from_user)
        await message.answer(
            format_shift_status_text(
                shift,
                context.bot_settings.timezone,
                title="Смена уже активна",
            ),
            reply_markup=main_menu_keyboard(active_shift=True),
        )
        return

    mode = "advanced" if message.text == "Advanced" else "advanced_research"
    context = await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await start_shift(message.from_user, mode=mode)
    await state.clear()
    await message.answer(
        format_shift_status_text(shift, context.bot_settings.timezone),
        reply_markup=main_menu_keyboard(active_shift=True),
    )


@router.message(F.text == "Конец смены")
async def handle_end_shift(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    shift = await get_active_shift(message.from_user.id)
    if not shift:
        await message.answer("Нет активной смены", reply_markup=main_menu_keyboard())
        return

    await state.set_state(CloseShiftStates.waiting_for_total)
    await message.answer("Введите итоговую выручку", reply_markup=main_menu_keyboard(active_shift=True))


@router.message(CloseShiftStates.waiting_for_total)
async def handle_close_shift_total(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return

    amount = parse_decimal(message.text)
    if amount is None:
        await message.answer("Введите число")
        return

    shift = await close_shift(message.from_user.id, amount)
    if shift is None:
        await state.clear()
        await message.answer("Нет активной смены", reply_markup=main_menu_keyboard())
        return

    summary = await close_shift_summary(shift)
    await state.clear()
    await message.answer(f"Смена завершена\n\n{summary}", reply_markup=main_menu_keyboard())
