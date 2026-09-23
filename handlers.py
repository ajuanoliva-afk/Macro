from __future__ import annotations

import asyncio
import logging
from datetime import date

from telegram import BotCommand, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from .alerts import condition_is_true, latest_alert_value
from .catalog import (
    EUROSTAT_SERIES,
    FRED_SERIES,
    GEO_LABELS,
    resolve_eurostat,
    resolve_fred,
    resolve_geo,
)
from .charts import make_chart
from .clients.base import DataSourceError
from .db import AlertStore
from .formatting import format_number, one_line, series_summary
from .models import Alert, DataSeries
from .timeutils import is_period, months_ago, period_start


LOGGER = logging.getLogger(__name__)
DEFAULT_PERIOD = "5y"
COMPARISON_GEOS = ("EA21", "ES", "DE", "FR", "IT")

HELP_TEXT = """Macro Terminal

/fred <alias|serie> [periodo] [@vintage]
/fred search <texto>
/eurostat <indicador> [país] [periodo]
/chart <serie> [país] [periodo]
/compare <series...> [periodo]
/compare hicp ES DE FR IT 5y
/macro usa
/macro europe
/alert add <serie> [país] above|below <nivel>
/alert list
/alert delete <id>

Periodos: 1m, 3m, 6m, 1y, 2y, 5y, 10y, 20y, max.
Vintage ALFRED: /fred gdp 10y @2020-03-15
Ejemplos: /chart cpi 10y · /compare 2y 10y 5y · /eurostat hicp ES 5y"""


def _services(context: ContextTypes.DEFAULT_TYPE):
    return context.bot_data["fred"], context.bot_data["eurostat"]


async def _authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    allowed: frozenset[int] = context.bot_data["allowed_chat_ids"]
    chat = update.effective_chat
    if chat and (not allowed or chat.id in allowed):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("Este bot es privado.")
    return False


async def _typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)


async def _send_error(update: Update, error: Exception) -> None:
    LOGGER.warning("Command error: %s", error)
    if update.effective_message:
        await update.effective_message.reply_text(f"No pude obtener el dato: {error}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    await update.effective_message.reply_text(HELP_TEXT)


async def fred_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    args = context.args
    if not args:
        aliases = ", ".join(FRED_SERIES)
        await update.effective_message.reply_text(
            f"Uso: /fred <alias|serie> [periodo] [@vintage]\nAliases: {aliases}"
        )
        return
    fred, _ = _services(context)
    try:
        await _typing(update, context)
        if args[0].lower() == "search":
            query = " ".join(args[1:]).strip()
            if not query:
                raise ValueError("Uso: /fred search <texto>")
            results = await fred.search(query)
            if not results:
                raise ValueError("Sin resultados")
            lines = ["Resultados FRED:"]
            for item in results:
                lines.append(
                    f"{item['id']} · {item['title']} ({item.get('frequency_short', '')})"
                )
            await update.effective_message.reply_text("\n".join(lines))
            return

        spec = resolve_fred(args[0])
        period = next((item for item in args[1:] if is_period(item)), "2y")
        vintage_token = next((item for item in args[1:] if item.startswith("@")), None)
        vintage = date.fromisoformat(vintage_token[1:]) if vintage_token else None
        series = await fred.fetch(
            spec, period_start(period, reference=vintage or date.today()), vintage
        )
        await update.effective_message.reply_text(series_summary(series))
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def eurostat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    args = context.args
    if not args:
        aliases = ", ".join(EUROSTAT_SERIES)
        await update.effective_message.reply_text(
            f"Uso: /eurostat <indicador> [país] [periodo]\nIndicadores: {aliases}"
        )
        return
    _, eurostat = _services(context)
    try:
        await _typing(update, context)
        spec = resolve_eurostat(args[0])
        period = next((item for item in args[1:] if is_period(item)), "5y")
        geo_token = next((item for item in args[1:] if not is_period(item)), "EA21")
        geo = resolve_geo(geo_token)
        series = (await eurostat.fetch(spec, [geo], period_start(period)))[0]
        await update.effective_message.reply_text(series_summary(series))
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def _fetch_chart_target(
    token: str,
    geo: str | None,
    period: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> DataSeries:
    fred, eurostat = _services(context)
    key = token.lower()
    if key in EUROSTAT_SERIES and (geo or key not in FRED_SERIES):
        return (
            await eurostat.fetch(
                resolve_eurostat(key), [resolve_geo(geo or "EA21")], period_start(period)
            )
        )[0]
    return await fred.fetch(resolve_fred(token), period_start(period))


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text(
            "Uso: /chart <serie> [país] [periodo]. Ej.: /chart hicp ES 5y"
        )
        return
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        period = next((item for item in args[1:] if is_period(item)), DEFAULT_PERIOD)
        geo = next((item for item in args[1:] if not is_period(item)), None)
        series = await _fetch_chart_target(args[0], geo, period, context)
        chart = await asyncio.to_thread(make_chart, [series])
        await update.effective_message.reply_photo(
            chart,
            caption=one_line(series),
        )
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    args = list(context.args)
    if len(args) < 2:
        await update.effective_message.reply_text(
            "Uso: /compare 2y 10y 5y o /compare hicp ES DE FR IT 5y"
        )
        return
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        period = next((item for item in reversed(args) if is_period(item)), DEFAULT_PERIOD)
        tokens = [item for item in args if not is_period(item)]
        fred, eurostat = _services(context)

        if tokens[0].lower() in EUROSTAT_SERIES:
            if len(tokens) < 2:
                raise ValueError("Indica al menos un país para comparar")
            spec = resolve_eurostat(tokens[0])
            geos = [resolve_geo(item) for item in tokens[1:]]
            series = await eurostat.fetch(spec, geos, period_start(period))
            title = f"{spec.title} · comparación europea"
        else:
            series = await asyncio.gather(
                *(
                    fred.fetch(resolve_fred(token), period_start(period))
                    for token in tokens
                )
            )
            title = "Comparación FRED"
        chart = await asyncio.to_thread(make_chart, list(series), title)
        caption = "\n".join(one_line(item) for item in series)
        await update.effective_message.reply_photo(chart, caption=caption[:1024])
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def macro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    region = context.args[0].lower() if context.args else "usa"
    try:
        await _typing(update, context)
        if region in {"usa", "us"}:
            await _macro_usa(update, context)
        elif region in {"europe", "europa", "euro", "eu"}:
            await _macro_europe(update, context)
        else:
            raise ValueError("Usa /macro usa o /macro europe")
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def _macro_usa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fred, _ = _services(context)
    aliases = (
        "cpi",
        "core_cpi",
        "pce",
        "core_pce",
        "gdp",
        "unemployment",
        "payrolls",
        "ism",
        "retail",
        "industrial",
        "fedfunds",
        "2y",
        "5y",
        "10y",
        "30y",
        "be5",
        "be10",
        "ig_spread",
        "hy_spread",
    )

    async def fetch_one(alias: str):
        try:
            return alias, await fred.fetch(
                resolve_fred(alias), months_ago(date.today(), 18)
            ), None
        except Exception as exc:
            return alias, None, str(exc)

    results = await asyncio.gather(*(fetch_one(alias) for alias in aliases))
    lines = ["USA · Macro snapshot", ""]
    for alias, series, error in results:
        if series:
            lines.append(one_line(series))
        else:
            lines.append(f"{alias}: no disponible ({error})")
    await update.effective_message.reply_text("\n".join(lines)[:4096])


async def _macro_europe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, eurostat = _services(context)
    aliases = tuple(EUROSTAT_SERIES)

    async def fetch_one(alias: str):
        spec = resolve_eurostat(alias)
        try:
            values = await eurostat.fetch(
                spec, COMPARISON_GEOS, months_ago(date.today(), 24)
            )
            return alias, values, None
        except Exception as exc:
            return alias, [], str(exc)

    results = await asyncio.gather(*(fetch_one(alias) for alias in aliases))
    lines = ["Europa · Macro snapshot", "Geos: EZ / ES / DE / FR / IT", ""]
    for alias, values, error in results:
        if error:
            lines.append(f"{alias}: no disponible ({error})")
            continue
        by_geo = {item.geo: item.latest for item in values}
        unit = values[0].unit if values else ""
        cells = []
        for geo in COMPARISON_GEOS:
            observation = by_geo.get(geo)
            short = "EZ" if geo == "EA21" else geo
            cells.append(
                f"{short} {format_number(observation.value)}"
                if observation
                else f"{short} —"
            )
        latest_date = max(item.latest.date for item in values)
        lines.append(
            f"{values[0].title}: " + " | ".join(cells) + f" {unit} · {latest_date}"
        )
    await update.effective_message.reply_text("\n".join(lines)[:4096])


def _operator(value: str) -> str:
    normalized = value.lower()
    if normalized in {"above", ">", "encima", "sobre"}:
        return "above"
    if normalized in {"below", "<", "debajo", "bajo"}:
        return "below"
    raise ValueError("El operador debe ser above o below")


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _authorized(update, context):
        return
    args = context.args
    store: AlertStore = context.bot_data["alerts"]
    chat_id = update.effective_chat.id
    if not args:
        await update.effective_message.reply_text(
            "Uso: /alert add 10y above 5 · /alert add hicp ES below 2 · "
            "/alert list · /alert delete 3"
        )
        return
    action = args[0].lower()
    try:
        if action == "list":
            alerts = store.list_for_chat(chat_id)
            if not alerts:
                await update.effective_message.reply_text("No tienes alertas activas.")
                return
            lines = ["Alertas activas:"]
            for item in alerts:
                geo = f" {item.geo}" if item.geo else ""
                sign = ">" if item.operator == "above" else "<"
                lines.append(f"#{item.id} {item.symbol}{geo} {sign} {item.threshold:g}")
            await update.effective_message.reply_text("\n".join(lines))
            return
        if action in {"delete", "del", "remove"}:
            if len(args) != 2:
                raise ValueError("Uso: /alert delete <id>")
            deleted = store.delete(chat_id, int(args[1]))
            await update.effective_message.reply_text(
                "Alerta eliminada." if deleted else "No encontré esa alerta."
            )
            return
        if action != "add":
            raise ValueError("Acciones válidas: add, list, delete")
        if len(args) not in {4, 5}:
            raise ValueError(
                "Uso: /alert add 10y above 5 o /alert add hicp ES above 3"
            )

        symbol = args[1].lower()
        if symbol in EUROSTAT_SERIES:
            if len(args) != 5:
                raise ValueError("Las alertas Eurostat necesitan país")
            provider = "eurostat"
            geo = resolve_geo(args[2])
            operator = _operator(args[3])
            threshold = float(args[4].replace(",", "."))
        else:
            if len(args) != 4:
                raise ValueError("Las alertas FRED no llevan país")
            provider = "fred"
            geo = None
            operator = _operator(args[2])
            threshold = float(args[3].replace(",", "."))
            resolve_fred(symbol)

        temporary = Alert(0, chat_id, provider, symbol, geo, operator, threshold, None, True)
        value, value_date, unit = await latest_alert_value(context, temporary)
        current = condition_is_true(operator, value, threshold)
        alert = store.add(
            chat_id, provider, symbol, geo, operator, threshold, current
        )
        state = "La condición ya se cumple." if current else "Aún no se cumple."
        await update.effective_message.reply_text(
            f"Alerta #{alert.id} creada. Valor actual: {format_number(value)} {unit} "
            f"({value_date}). {state}\nAvisaré cuando cruce el umbral."
        )
    except (ValueError, DataSourceError) as exc:
        await _send_error(update, exc)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled bot error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Ha ocurrido un error interno. Revisa el log del bot."
        )


BOT_COMMANDS = [
    BotCommand("fred", "Consulta o busca una serie FRED"),
    BotCommand("eurostat", "Consulta un indicador europeo"),
    BotCommand("chart", "Genera un gráfico"),
    BotCommand("compare", "Compara series o países"),
    BotCommand("macro", "Dashboard macro USA o Europa"),
    BotCommand("alert", "Crea y gestiona alertas"),
    BotCommand("help", "Ayuda y ejemplos"),
]
