from __future__ import annotations

import asyncio
import logging
from datetime import date

from telegram.ext import CallbackContext

from .catalog import resolve_eurostat, resolve_fred
from .db import AlertStore
from .formatting import format_number
from .models import Alert
from .timeutils import months_ago


LOGGER = logging.getLogger(__name__)


def condition_is_true(operator: str, value: float, threshold: float) -> bool:
    if operator == "above":
        return value > threshold
    if operator == "below":
        return value < threshold
    raise ValueError(f"Operador desconocido: {operator}")


async def latest_alert_value(context: CallbackContext, alert: Alert) -> tuple[float, date, str]:
    if alert.provider == "fred":
        spec = resolve_fred(alert.symbol)
        series = await context.bot_data["fred"].fetch(
            spec, start=months_ago(date.today(), 18)
        )
    else:
        spec = resolve_eurostat(alert.symbol)
        series = (
            await context.bot_data["eurostat"].fetch(
                spec, [alert.geo or "EA21"], start=months_ago(date.today(), 18)
            )
        )[0]
    return series.latest.value, series.latest.date, series.unit


async def check_alerts(context: CallbackContext) -> None:
    store: AlertStore = context.bot_data["alerts"]
    alerts = store.list_active()
    semaphore = asyncio.Semaphore(4)

    async def check_one(alert: Alert) -> None:
        async with semaphore:
            try:
                value, value_date, unit = await latest_alert_value(context, alert)
                current = condition_is_true(alert.operator, value, alert.threshold)
                should_fire = current and alert.last_condition is False
                store.set_condition(alert.id, current)
                if should_fire:
                    direction = "superó" if alert.operator == "above" else "cayó por debajo de"
                    geo = f" {alert.geo}" if alert.geo else ""
                    await context.bot.send_message(
                        chat_id=alert.chat_id,
                        text=(
                            f"🔔 {alert.symbol}{geo} {direction} {alert.threshold:g}\n"
                            f"Valor: {format_number(value)} {unit} · {value_date.isoformat()}"
                        ),
                    )
            except Exception:
                LOGGER.exception("No se pudo comprobar la alerta %s", alert.id)

    await asyncio.gather(*(check_one(alert) for alert in alerts))

