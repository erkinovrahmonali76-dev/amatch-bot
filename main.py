import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from config import BOT_TOKEN
from handlers.common import router


PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan")

    if not WEBHOOK_BASE_URL or not WEBHOOK_SECRET:
        raise RuntimeError(
            "WEBHOOK_BASE_URL yoki WEBHOOK_SECRET sozlanmagan"
        )

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()

    async def on_startup(app):
        await bot.set_webhook(
            url=f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        print("A_Match Bot webhook ishga tushdi")

    app.on_startup.append(on_startup)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
