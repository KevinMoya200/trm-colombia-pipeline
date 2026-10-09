"""Validaciones de calidad. Si una regla dura falla, el pipeline se detiene antes de cargar."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

log = logging.getLogger(__name__)

TRM_MIN, TRM_MAX = 500, 10_000  # rango plausible, en pesos por dólar
MAX_DAILY_CHANGE = 0.10  # un cambio de más de 10 % en un día se marca como alerta
MAX_STALE_DAYS = 15  # si el dato más reciente es más viejo que esto, algo falló en la fuente


class DataQualityError(Exception):
    """Se lanza cuando los datos no cumplen una regla dura."""


@dataclass
class QualityReport:
    rows: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check_daily(df: pd.DataFrame, today: date | None = None) -> QualityReport:
    """Revisa la tabla diaria. Errores detienen el pipeline; alertas solo se registran."""
    report = QualityReport(rows=len(df))
    if df.empty:
        report.errors.append("La tabla diaria está vacía.")
        return report

    nulls = int(df["trm"].isna().sum())
    if nulls:
        report.errors.append(f"{nulls} días sin valor de TRM.")

    duplicates = int(pd.Series(df["fecha"]).duplicated().sum())
    if duplicates:
        report.errors.append(f"{duplicates} fechas duplicadas.")

    out_of_range = int(((df["trm"] < TRM_MIN) | (df["trm"] > TRM_MAX)).sum())
    if out_of_range:
        report.errors.append(f"{out_of_range} valores fuera del rango {TRM_MIN}-{TRM_MAX}.")

    dates = pd.to_datetime(pd.Series(df["fecha"])).sort_values()
    expected_days = len(pd.date_range(dates.min(), dates.max(), freq="D"))
    missing_days = expected_days - dates.nunique()
    if missing_days > 0:
        report.warnings.append(f"Faltan {missing_days} días en el calendario.")

    changes = df.sort_values("fecha")["trm"].pct_change().abs()
    jumps = int((changes > MAX_DAILY_CHANGE).sum())
    if jumps:
        report.warnings.append(f"{jumps} días con cambio mayor a {MAX_DAILY_CHANGE:.0%}.")

    if today is not None:
        stale = (pd.Timestamp(today) - dates.max()).days
        if stale > MAX_STALE_DAYS:
            report.errors.append(f"El dato más reciente tiene {stale} días de antigüedad.")
    return report


def enforce(report: QualityReport) -> None:
    """Registra las alertas y detiene el pipeline si hay errores."""
    for warning in report.warnings:
        log.warning("Calidad: %s", warning)
    if not report.ok:
        raise DataQualityError("; ".join(report.errors))
    log.info("Calidad OK: %s filas, %s alertas", report.rows, len(report.warnings))
