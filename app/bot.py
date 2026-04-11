from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonCommands

from app.config import settings
from app.handlers import common, order, shift, stats


async def start_bot() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(common.router)
    dp.include_router(shift.router)
    dp.include_router(order.router)
    dp.include_router(stats.router)

    commands = [
        BotCommand(command="start", description="Pokreni bota"),
        BotCommand(command="help", description="Spisak dostupnih komandi"),
        BotCommand(command="shift_start", description="Pokreni smenu"),
        BotCommand(command="shift_end", description="Završi smenu"),
        BotCommand(command="order_add", description="Dodaj porudžbinu"),
        BotCommand(command="stats", description="Prikaži statistiku"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code="sr")
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands(text="Meni"))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
