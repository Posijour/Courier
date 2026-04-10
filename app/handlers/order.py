from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.keyboards.main import main_menu_keyboard
from app.services.accounts import resolve_tenant_context_for_telegram_user, supports_advanced_mode
from app.services.orders import create_order
from app.services.shifts import get_active_shift
from app.states import AdvancedOrderStates, ResearchOrderStates
from app.utils.formatters import parse_decimal
from app.utils.shift_status import format_shift_status_text

router = Router()
DISTRICTS = ("Medijana", "Palilula", "Pantelej", "Crveni Krst", "Niska Banja")
DISTRICT_VALUES = set(DISTRICTS)
PLATFORMS = {"Wolt", "Glovo"}


def _district_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Medijana"), KeyboardButton(text="Palilula")],
            [KeyboardButton(text="Pantelej"), KeyboardButton(text="Crveni Krst")],
            [KeyboardButton(text="Niska Banja")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


def _platform_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Wolt"), KeyboardButton(text="Glovo")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


def _skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


async def _cancel_order_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    active_shift = await get_active_shift(message.from_user.id) if message.from_user else None
    await message.answer("Отменено", reply_markup=main_menu_keyboard(active_shift=active_shift is not None))


async def _ensure_active_shift(message: Message, state: FSMContext) -> bool:
    if not message.from_user:
        return False

    shift = await get_active_shift(message.from_user.id)
    if shift:
        return True

    await state.clear()
    await message.answer("Сначала начните смену", reply_markup=main_menu_keyboard())
    return False


def _is_valid_district(value: str) -> bool:
    return value in DISTRICT_VALUES


@router.message(F.text == "+ Заказ")
async def handle_add_order(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    context = await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await get_active_shift(message.from_user.id)
    if not shift:
        await message.answer("Сначала начните смену", reply_markup=main_menu_keyboard())
        return

    if shift.mode == "advanced_research":
        await state.set_state(ResearchOrderStates.waiting_for_platform)
        await message.answer("Платформа", reply_markup=_platform_keyboard())
        return

    if shift.mode == "advanced" or supports_advanced_mode(context):
        await state.set_state(AdvancedOrderStates.waiting_for_district)
        await message.answer("Район", reply_markup=_district_keyboard())
        return

    await create_order(telegram_id=message.from_user.id, source_mode="basic")
    shift = await get_active_shift(message.from_user.id)
    if not shift:
        await message.answer("Заказ добавлен", reply_markup=main_menu_keyboard())
        return
    shift_status = format_shift_status_text(
        shift,
        context.bot_settings.timezone,
        blank_after_title=False,
    )
    await message.answer(
        f"Заказ добавлен \n\n{shift_status}",
        reply_markup=main_menu_keyboard(active_shift=True),
    )


@router.message(AdvancedOrderStates.waiting_for_district)
async def handle_advanced_district(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if not await _ensure_active_shift(message, state):
        return

    if not _is_valid_district(message.text):
        await message.answer("Выберите район", reply_markup=_district_keyboard())
        return

    await state.update_data(district=message.text)
    await state.set_state(AdvancedOrderStates.waiting_for_platform)
    await message.answer("Платформа", reply_markup=_platform_keyboard())


@router.message(AdvancedOrderStates.waiting_for_platform)
async def handle_advanced_platform(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if message.text not in PLATFORMS:
        await message.answer("Выберите Wolt или Glovo", reply_markup=_platform_keyboard())
        return

    await state.update_data(platform=message.text)
    await state.set_state(AdvancedOrderStates.waiting_for_earnings)
    await message.answer("Сумма заказа", reply_markup=_skip_keyboard())


@router.message(AdvancedOrderStates.waiting_for_earnings)
async def handle_advanced_earnings(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    order_earnings = None
    if message.text != "Пропустить":
        order_earnings = parse_decimal(message.text)
        if order_earnings is None:
            await message.answer("Введите число или нажмите Пропустить", reply_markup=_skip_keyboard())
            return

    data = await state.get_data()
    await create_order(
        telegram_id=message.from_user.id,
        source_mode="advanced",
        district=data.get("district"),
        platform=data.get("platform"),
        order_earnings=order_earnings,
    )
    context = await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await get_active_shift(message.from_user.id)
    await state.clear()
    if not shift:
        await message.answer("Заказ добавлен", reply_markup=main_menu_keyboard())
        return
    shift_status = format_shift_status_text(
        shift,
        context.bot_settings.timezone,
        blank_after_title=False,
    )
    await message.answer(
        f"Заказ добавлен \n\n{shift_status}",
        reply_markup=main_menu_keyboard(active_shift=True),
    )


@router.message(ResearchOrderStates.waiting_for_platform)
async def handle_research_platform(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if not await _ensure_active_shift(message, state):
        return

    if message.text not in PLATFORMS:
        await message.answer("Выберите Wolt или Glovo", reply_markup=_platform_keyboard())
        return

    await state.update_data(platform=message.text)
    await state.set_state(ResearchOrderStates.waiting_for_position_district)
    await message.answer("Район позиции курьера", reply_markup=_district_keyboard())


@router.message(ResearchOrderStates.waiting_for_position_district)
async def handle_research_position_district(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if not _is_valid_district(message.text):
        await message.answer("Выберите район", reply_markup=_district_keyboard())
        return

    await state.update_data(position_district=message.text)
    await state.set_state(ResearchOrderStates.waiting_for_pickup_district)
    await message.answer("Район ресторана", reply_markup=_district_keyboard())


@router.message(ResearchOrderStates.waiting_for_pickup_district)
async def handle_research_pickup_district(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if not _is_valid_district(message.text):
        await message.answer("Выберите район", reply_markup=_district_keyboard())
        return

    await state.update_data(pickup_district=message.text)
    await state.set_state(ResearchOrderStates.waiting_for_dropoff_district)
    await message.answer("Район доставки", reply_markup=_district_keyboard())


@router.message(ResearchOrderStates.waiting_for_dropoff_district)
async def handle_research_dropoff_district(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    if not _is_valid_district(message.text):
        await message.answer("Выберите район", reply_markup=_district_keyboard())
        return

    await state.update_data(dropoff_district=message.text)
    await state.set_state(ResearchOrderStates.waiting_for_earnings)
    await message.answer("Сумма заказа", reply_markup=_skip_keyboard())


@router.message(ResearchOrderStates.waiting_for_earnings)
async def handle_research_earnings(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return

    if message.text == "Отмена":
        await _cancel_order_flow(message, state)
        return

    order_earnings = None
    if message.text != "Пропустить":
        order_earnings = parse_decimal(message.text)
        if order_earnings is None:
            await message.answer("Введите число или нажмите Пропустить", reply_markup=_skip_keyboard())
            return

    data = await state.get_data()
    position_district = data.get("position_district")
    await create_order(
        telegram_id=message.from_user.id,
        source_mode="advanced_research",
        district=position_district,
        position_district=position_district,
        pickup_district=data.get("pickup_district"),
        dropoff_district=data.get("dropoff_district"),
        platform=data.get("platform"),
        order_earnings=order_earnings,
    )
    context = await resolve_tenant_context_for_telegram_user(message.from_user)
    shift = await get_active_shift(message.from_user.id)
    await state.clear()
    if not shift:
        await message.answer("Заказ добавлен", reply_markup=main_menu_keyboard())
        return
    shift_status = format_shift_status_text(
        shift,
        context.bot_settings.timezone,
        blank_after_title=False,
    )
    await message.answer(
        f"Заказ добавлен \n\n{shift_status}",
        reply_markup=main_menu_keyboard(active_shift=True),
    )
