# Macro Telegram Bot

Bot de Telegram para consultar y comparar datos macroeconómicos de FRED/ALFRED y Eurostat, generar gráficos y recibir alertas por cruce de umbral.

## Qué incluye

- Estados Unidos: CPI, Core CPI, PCE, Core PCE, PIB real, desempleo, payrolls, ISM, ventas minoristas, producción industrial, Fed Funds, Treasury 2Y/5Y/10Y/30Y, breakevens 5Y/10Y/5Y5Y y spreads IG/HY.
- Europa: HICP, Core HICP, PIB real, desempleo, salarios, producción industrial, ventas minoristas, deuda y saldo público.
- Comparaciones entre eurozona, España, Alemania, Francia e Italia.
- Gráficos PNG generados dentro del bot.
- Alertas persistentes en SQLite que se activan al cruzar un nivel.
- Vintages de ALFRED mediante `@AAAA-MM-DD`.
- Búsqueda libre de códigos FRED.

## Comandos

```text
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
```

Ejemplos:

```text
/fred cpi 2y
/fred GDPC1 10y @2020-03-15
/fred search financial conditions
/eurostat hicp ES 5y
/chart core_pce 10y
/chart unemployment ES 5y
/compare 2y 10y 5y
/compare hicp ES DE FR IT 5y
/alert add 10y above 5
/alert add hicp ES above 3
```

Periodos admitidos: `1m`, `3m`, `6m`, `1y`, `2y`, `5y`, `10y`, `20y` y `max`.

## Instalación rápida con Docker

Requisitos: Docker con Compose, un token de [BotFather](https://t.me/BotFather) y una [API key de FRED](https://fredaccount.stlouisfed.org/apikeys).

```bash
cp .env.example .env
```

Completa en `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=...
FRED_API_KEY=...
```

Después:

```bash
docker compose up -d --build
docker compose logs -f macrobot
```

La base de alertas queda guardada en `./data/macrobot.sqlite3`.

## Instalación local

Requiere Python 3.12 o posterior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m macrobot.main
```

## Privacidad

Si `ALLOWED_CHAT_IDS` está vacío, cualquier persona que encuentre el bot podrá usarlo. Para hacerlo privado, añade uno o varios identificadores de chat separados por comas:

```dotenv
ALLOWED_CHAT_IDS=123456789,987654321
```

Puedes conocer tu identificador temporalmente arrancando el bot sin esta restricción y consultándolo con un bot de identificación de Telegram; después configura la lista y reinicia.

## Definiciones aplicadas

| Alias | Fuente/serie | Presentación |
|---|---|---|
| `cpi` | FRED `CPIAUCSL` | variación interanual calculada |
| `core_cpi` | FRED `CPILFESL` | variación interanual calculada |
| `pce` | FRED `PCEPI` | variación interanual calculada |
| `core_pce` | FRED `PCEPILFE` | variación interanual calculada |
| `gdp` (USA) | FRED `GDPC1` | crecimiento trimestral anualizado |
| `payrolls` | FRED `PAYEMS` | cambio mensual en miles |
| `retail`, `industrial` (USA) | FRED `RSAFS`, `INDPRO` | variación mensual calculada |
| `hicp` | Eurostat `prc_hicp_minr` | tasa interanual |
| `core_hicp` | Eurostat `prc_hicp_minr` | total sin energía ni alimentos |
| `gdp` (Europa) | Eurostat `namq_10_gdp` | volumen real, variación trimestral SCA |
| `wages` | Eurostat `lc_lci_r2_q` | salarios, variación interanual CA |
| `debt`, `deficit` | Eurostat `gov_10dd_edpt1` | porcentaje del PIB; saldo negativo = déficit |

Eurostat sustituyó en 2026 los antiguos datasets HICP por `prc_hicp_minr` (ECOICOP v2); el catálogo ya usa el nuevo conjunto. La eurozona por defecto es `EA21`, mientras que las comparaciones nacionales emplean `ES`, `DE`, `FR` e `IT`.

### Nota sobre ISM

El alias `ism` intenta la antigua serie FRED `NAPM`. La disponibilidad reciente depende de los derechos de redistribución de ISM y puede aparecer como no disponible. El bot no inventa un proxy silencioso: muestra el fallo o la antigüedad del dato. Para producción, conviene añadir un adaptador con una fuente/licencia válida de ISM.

## ALFRED y datos en tiempo real histórico

El sufijo `@AAAA-MM-DD` fija `realtime_start` y `realtime_end` a la misma fecha. Así, por ejemplo, `/fred gdp 10y @2020-03-15` reconstruye el vintage que FRED/ALFRED conocía ese día, en vez de mostrar la serie revisada actual.

## Desarrollo y pruebas

```bash
pip install -e '.[dev]'
pytest -q
```

El proyecto está separado en clientes de fuente, catálogo, transformaciones, gráficos, almacenamiento y handlers. Esto permite añadir adaptadores para ECB, BEA, BLS, INE, BoE, OECD o BIS sin reescribir los comandos de Telegram.

