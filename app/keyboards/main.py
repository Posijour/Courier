from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(active_shift: bool = False) -> ReplyKeyboardMarkup:
    if active_shift:
        keyboard = [
            [KeyboardButton(text="+ Porudžbina"), KeyboardButton(text="Završi smenu")],
            [KeyboardButton(text="Moja statistika")],
            [KeyboardButton(text="Danas vs juče"), KeyboardButton(text="Nedelja")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="Pokreni smenu")],
            [KeyboardButton(text="Moja statistika")],
            [KeyboardButton(text="Danas vs juče"), KeyboardButton(text="Nedelja")],
        ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
