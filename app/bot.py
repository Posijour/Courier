from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
