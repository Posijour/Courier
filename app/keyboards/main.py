from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(active_shift: bool = False) -> ReplyKeyboardMarkup:
    if active_shift:
        keyboard = [
            [KeyboardButton(text="+ Заказ"), KeyboardButton(text="Конец смены")],
            [KeyboardButton(text="Моя статистика")],
            [KeyboardButton(text="Сегодня vs вчера"), KeyboardButton(text="Неделя")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="Старт смены")],
            [KeyboardButton(text="Моя статистика")],
            [KeyboardButton(text="Сегодня vs вчера"), KeyboardButton(text="Неделя")],
        ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
