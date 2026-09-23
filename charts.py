from __future__ import annotations

from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .catalog import GEO_LABELS
from .models import DataSeries


COLORS = ["#38bdf8", "#f59e0b", "#34d399", "#f472b6", "#a78bfa", "#fb7185"]


def make_chart(series: list[DataSeries], title: str | None = None) -> BytesIO:
    if not series:
        raise ValueError("No hay series para dibujar")

    plt.style.use("dark_background")
    figure, axis = plt.subplots(figsize=(10, 5.6), dpi=150)
    figure.patch.set_facecolor("#0f172a")
    axis.set_facecolor("#0f172a")

    for index, item in enumerate(series):
        label = item.title
        if item.geo:
            label += f" · {GEO_LABELS.get(item.geo, item.geo)}"
        axis.plot(
            [obs.date for obs in item.observations],
            [obs.value for obs in item.observations],
            color=COLORS[index % len(COLORS)],
            linewidth=2.0,
            label=label,
        )

    axis.axhline(0, color="#64748b", linewidth=0.7, alpha=0.55)
    axis.grid(True, color="#334155", linewidth=0.6, alpha=0.55)
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["bottom", "left"]].set_color("#64748b")
    axis.tick_params(colors="#cbd5e1", labelsize=9)
    axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(axis.xaxis.get_major_locator()))
    axis.legend(frameon=False, fontsize=9, loc="best")
    axis.set_title(title or series[0].title, loc="left", fontsize=15, fontweight="bold")
    units = {item.unit for item in series if item.unit}
    if len(units) == 1:
        axis.set_ylabel(next(iter(units)), color="#cbd5e1")
    sources = " / ".join(sorted({item.provider.upper() for item in series}))
    axis.text(
        0,
        -0.16,
        f"Fuente: {sources}",
        transform=axis.transAxes,
        fontsize=8,
        color="#94a3b8",
    )
    figure.tight_layout()

    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    buffer.seek(0)
    buffer.name = "macro_chart.png"
    return buffer

