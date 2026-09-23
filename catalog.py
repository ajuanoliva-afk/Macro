from __future__ import annotations

from .models import EurostatSpec, FredSpec


FRED_SERIES: dict[str, FredSpec] = {
    "cpi": FredSpec("cpi", "CPIAUCSL", "CPI", "yoy", "% interanual"),
    "core_cpi": FredSpec(
        "core_cpi", "CPILFESL", "Core CPI", "yoy", "% interanual"
    ),
    "pce": FredSpec("pce", "PCEPI", "PCE", "yoy", "% interanual"),
    "core_pce": FredSpec(
        "core_pce", "PCEPILFE", "Core PCE", "yoy", "% interanual"
    ),
    "gdp": FredSpec(
        "gdp", "GDPC1", "Real GDP", "qoq_ann", "% trimestral anualizado"
    ),
    "unemployment": FredSpec(
        "unemployment", "UNRATE", "Unemployment", "level", "%"
    ),
    "payrolls": FredSpec(
        "payrolls", "PAYEMS", "Nonfarm payrolls", "change", "miles, variación"
    ),
    "ism": FredSpec(
        "ism",
        "NAPM",
        "ISM Manufacturing PMI",
        "level",
        "índice",
        "La disponibilidad actual depende de la licencia de ISM en FRED.",
    ),
    "retail": FredSpec(
        "retail", "RSAFS", "Retail sales", "mom", "% mensual"
    ),
    "industrial": FredSpec(
        "industrial", "INDPRO", "Industrial production", "mom", "% mensual"
    ),
    "fedfunds": FredSpec(
        "fedfunds", "DFF", "Effective Fed Funds", "level", "%"
    ),
    "2y": FredSpec("2y", "DGS2", "US Treasury 2Y", "level", "%"),
    "5y": FredSpec("5y", "DGS5", "US Treasury 5Y", "level", "%"),
    "10y": FredSpec("10y", "DGS10", "US Treasury 10Y", "level", "%"),
    "30y": FredSpec("30y", "DGS30", "US Treasury 30Y", "level", "%"),
    "be5": FredSpec(
        "be5", "T5YIE", "5Y breakeven inflation", "level", "%"
    ),
    "be10": FredSpec(
        "be10", "T10YIE", "10Y breakeven inflation", "level", "%"
    ),
    "5y5y": FredSpec(
        "5y5y", "T5YIFR", "5Y5Y forward inflation", "level", "%"
    ),
    "ig_spread": FredSpec(
        "ig_spread",
        "BAMLC0A0CM",
        "US investment-grade OAS",
        "level",
        "%",
    ),
    "hy_spread": FredSpec(
        "hy_spread",
        "BAMLH0A0HYM2",
        "US high-yield OAS",
        "level",
        "%",
    ),
}


EUROSTAT_SERIES: dict[str, EurostatSpec] = {
    "hicp": EurostatSpec(
        "hicp",
        "prc_hicp_minr",
        "HICP",
        {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL"},
        "% interanual",
    ),
    "core_hicp": EurostatSpec(
        "core_hicp",
        "prc_hicp_minr",
        "Core HICP (sin energía ni alimentos)",
        {
            "freq": "M",
            "unit": "RCH_A",
            "coicop18": "TOT_X_NRG_FOOD",
        },
        "% interanual",
    ),
    "gdp": EurostatSpec(
        "gdp",
        "namq_10_gdp",
        "Real GDP",
        {
            "freq": "Q",
            "unit": "CLV_PCH_PRE",
            "s_adj": "SCA",
            "na_item": "B1GQ",
        },
        "% trimestral",
    ),
    "unemployment": EurostatSpec(
        "unemployment",
        "une_rt_m",
        "Unemployment",
        {
            "freq": "M",
            "s_adj": "SA",
            "age": "TOTAL",
            "unit": "PC_ACT",
            "sex": "T",
        },
        "%",
    ),
    "wages": EurostatSpec(
        "wages",
        "lc_lci_r2_q",
        "Wages and salaries",
        {
            "freq": "Q",
            "s_adj": "CA",
            "unit": "PCH_SM",
            "nace_r2": "B-S",
            "lcstruct": "D11",
        },
        "% interanual",
    ),
    "industrial": EurostatSpec(
        "industrial",
        "sts_inpr_m",
        "Industrial production",
        {
            "freq": "M",
            "indic_bt": "PRD",
            "nace_r2": "B-D",
            "s_adj": "CA",
            "unit": "PCH_SM",
        },
        "% interanual",
    ),
    "retail": EurostatSpec(
        "retail",
        "sts_trtu_m",
        "Retail sales volume",
        {
            "freq": "M",
            "indic_bt": "VOL_SLS",
            "nace_r2": "G47",
            "s_adj": "CA",
            "unit": "PCH_SM",
        },
        "% interanual",
    ),
    "debt": EurostatSpec(
        "debt",
        "gov_10dd_edpt1",
        "Government debt",
        {
            "freq": "A",
            "unit": "PC_GDP",
            "sector": "S13",
            "na_item": "GD",
        },
        "% del PIB",
    ),
    "deficit": EurostatSpec(
        "deficit",
        "gov_10dd_edpt1",
        "Government balance",
        {
            "freq": "A",
            "unit": "PC_GDP",
            "sector": "S13",
            "na_item": "B9",
        },
        "% del PIB",
        "Negativo = déficit; positivo = superávit.",
    ),
}


GEO_ALIASES = {
    "EA": "EA21",
    "EZ": "EA21",
    "EURO": "EA21",
    "EUROAREA": "EA21",
    "EU": "EU27_2020",
    "SPAIN": "ES",
    "ESPANA": "ES",
    "ESPAÑA": "ES",
    "GERMANY": "DE",
    "ALEMANIA": "DE",
    "FRANCE": "FR",
    "FRANCIA": "FR",
    "ITALY": "IT",
    "ITALIA": "IT",
}

GEO_LABELS = {
    "EA21": "Eurozona",
    "EA20": "Eurozona-20",
    "EU27_2020": "UE-27",
    "ES": "España",
    "DE": "Alemania",
    "FR": "Francia",
    "IT": "Italia",
}


def resolve_fred(value: str) -> FredSpec:
    key = value.strip().lower()
    if key in FRED_SERIES:
        return FRED_SERIES[key]
    series_id = value.strip().upper()
    if not series_id or not series_id.replace("_", "").isalnum():
        raise ValueError("Código FRED no válido")
    return FredSpec(series_id.lower(), series_id, series_id)


def resolve_eurostat(value: str) -> EurostatSpec:
    key = value.strip().lower()
    if key not in EUROSTAT_SERIES:
        known = ", ".join(EUROSTAT_SERIES)
        raise ValueError(f"Indicador Eurostat desconocido. Disponibles: {known}")
    return EUROSTAT_SERIES[key]


def resolve_geo(value: str | None) -> str:
    if not value:
        return "EA21"
    raw = value.strip().upper()
    return GEO_ALIASES.get(raw, raw)

