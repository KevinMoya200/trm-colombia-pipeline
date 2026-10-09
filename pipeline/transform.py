"""Transformación: de registros con vigencia a una fila por día."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {"valor", "vigenciadesde", "vigenciahasta"}
DAILY_COLUMNS = ["fecha", "trm", "vigencia_desde"]


def to_daily(records: list[dict]) -> pd.DataFrame:
    """Convierte los registros de la API en una tabla con una fila por día.

    La API entrega cada TRM con un rango de vigencia. Un mismo valor puede
    regir de sábado a lunes, o más días si hay festivo, y llega como un solo
    registro. Aquí se expande a un día por fila para poder cruzarla con
    cualquier fecha.
    """
    if not records:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    df = pd.DataFrame.from_records(records)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en la respuesta de la API: {sorted(missing)}")

    df["trm"] = pd.to_numeric(df["valor"], errors="coerce")
    df["desde"] = pd.to_datetime(df["vigenciadesde"], errors="coerce").dt.normalize()
    df["hasta"] = pd.to_datetime(df["vigenciahasta"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["desde", "hasta"])

    rows = [
        (dia, trm, desde)
        for desde, hasta, trm in df[["desde", "hasta", "trm"]].itertuples(index=False)
        for dia in pd.date_range(desde, hasta, freq="D")
    ]
    daily = pd.DataFrame(rows, columns=DAILY_COLUMNS)

    # Si dos vigencias cubren el mismo día, gana la que empezó más tarde.
    daily = (
        daily.sort_values(["fecha", "vigencia_desde"])
        .drop_duplicates(subset="fecha", keep="last")
        .reset_index(drop=True)
    )
    daily["fecha"] = daily["fecha"].dt.date
    daily["vigencia_desde"] = daily["vigencia_desde"].dt.date
    return daily
