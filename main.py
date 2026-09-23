from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler

from .alerts import check_alerts
from .clients.eurostat import EurostatClient
from .clients.fred import FredClient
from .config import Settings
from .db import AlertStore
from .handlers import (
    BOT_COMMANDS,
    alert_command,
    chart_command,
    compare_command,
    error_handler,
    eurostat_command,
    fred_command,
    macro_command,
    start_command,
)


def build_application(settings: Settings) -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data.update(
        {
            "fred": FredClient(settings.fred_api_key, settings.http_timeout_seconds),
            "eurostat": EurostatClient(settings.http_timeout_seconds),
            "alerts": AlertStore(settings.database_path),
            "allowed_chat_ids": settings.allowed_chat_ids,
        }
    )

    application.add_handler(CommandHandler(["start", "help"], start_command))
    application.add_handler(CommandHandler("fred", fred_command))
    application.add_handler(CommandHandler("eurostat", eurostat_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("macro", macro_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_error_handler(error_handler)

    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(BOT_COMMANDS)
        if app.job_queue is None:
            raise RuntimeError("JobQueue no está instalado")
        app.job_queue.run_repeating(
            check_alerts,
            interval=settings.alert_poll_seconds,
            first=15,
            name="macro-alerts",
        )

    async def post_shutdown(app: Application) -> None:
        await app.bot_data["fred"].close()
        await app.bot_data["eurostat"].close()
        app.bot_data["alerts"].close()

    application.post_init = post_init
    application.post_shutdown = post_shutdown
    return application


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = build_application(settings)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

