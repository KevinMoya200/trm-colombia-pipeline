"""Reportes: exporta los marts a CSV (para Power BI) y dibuja el gráfico del último año."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from . import config  # noqa: E402

MARTS = ["trm_mensual", "trm_volatilidad", "trm_resumen"]

# Colores validados (paleta categórica, slots 1 y 2) y tintas de texto
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
SERIES_1, SERIES_2 = "#2a78d6", "#eb6834"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
FUENTE_REAL = "Fuente: Superintendencia Financiera de Colombia, vía datos.gov.co."
FUENTE_SINTETICA = "Datos sintéticos de prueba: no es la TRM real."


def _pesos(value: float, decimals: int = 0) -> str:
    """Formato colombiano: punto para miles y coma para decimales."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def export_csv(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for mart in MARTS:
        path = out_dir / f"{mart}.csv"
        con.execute(f"COPY (SELECT * FROM marts.{mart}) TO '{path.as_posix()}' (HEADER, DELIMITER ',')")
        paths.append(path)
    return paths


def plot_last_year(con: duckdb.DuckDBPyConnection, out_path: Path, sample: bool = False) -> Path:
    df = con.execute(
        """
        SELECT
            fecha,
            trm,
            avg(trm) OVER (ORDER BY fecha ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS media_30d
        FROM core.trm_diaria
        QUALIFY fecha > max(fecha) OVER () - 365
        ORDER BY fecha
        """
    ).df()
    if df.empty:
        raise ValueError("No hay datos para graficar.")

    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    ax.plot(df["fecha"], df["trm"], color=SERIES_1, linewidth=1.5, label="TRM diaria")
    ax.plot(df["fecha"], df["media_30d"], color=SERIES_2, linewidth=1.5, label="Media móvil 30 días")

    # Etiqueta directa del último valor, en tinta de texto (no en el color de la serie)
    last = df.iloc[-1]
    ax.annotate(f"${_pesos(float(last['trm']), 2)}", xy=(last["fecha"], last["trm"]),
                xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=9, color=INK)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${_pesos(v)}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{MESES[mdates.num2date(v).month - 1]} {mdates.num2date(v):%y}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

    ax.set_title("TRM de Colombia, últimos 12 meses", loc="left", fontsize=13,
                 color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.02, "Pesos colombianos por dólar", transform=ax.transAxes,
            fontsize=9.5, color=INK_2)
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK_2)
    fig.text(0.01, 0.01,
             f"{FUENTE_SINTETICA if sample else FUENTE_REAL} Corte: {last['fecha']:%Y-%m-%d}. "
             f"Generado el {date.today():%Y-%m-%d}.",
             fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.03, 0.97, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def write_summary(con: duckdb.DuckDBPyConnection, out_path: Path, sample: bool = False) -> Path:
    r = con.execute("SELECT * FROM marts.trm_resumen").df().iloc[0]
    var = r["variacion_anio_pct"]
    var_text = "sin dato" if var != var else f"{_pesos(float(var), 2)} %"
    lines = [
        "# Resumen del último corte",
        "",
        "Este archivo lo genera el pipeline en cada ejecución. "
        + (FUENTE_SINTETICA if sample else FUENTE_REAL),
        "",
        "| Indicador | Valor |",
        "| --- | --- |",
        f"| Fecha de corte | {r['fecha_corte']:%Y-%m-%d} |",
        f"| TRM actual | ${_pesos(float(r['trm_actual']), 2)} |",
        f"| Mínimo 52 semanas | ${_pesos(float(r['minimo_52_semanas']), 2)} |",
        f"| Máximo 52 semanas | ${_pesos(float(r['maximo_52_semanas']), 2)} |",
        f"| Variación en el año | {var_text} |",
        f"| Días en la bodega | {_pesos(float(r['dias_en_bodega']))} |",
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def publish(con: duckdb.DuckDBPyConnection, sample: bool = False) -> list[Path]:
    """Genera todas las salidas. En modo de prueba van a carpetas aparte para no mezclar datos."""
    out_dir = config.OUTPUT_DIR / "sample" if sample else config.OUTPUT_DIR
    docs_dir = config.DOCS_DIR / "sample" if sample else config.DOCS_DIR
    paths = export_csv(con, out_dir)
    paths.append(plot_last_year(con, docs_dir / "trm_ultimo_anio.png", sample))
    paths.append(write_summary(con, docs_dir / "resumen.md", sample))
    return paths
