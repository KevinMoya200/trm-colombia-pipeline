"""Carga: DuckDB como bodega local, con upsert idempotente y modelos en SQL."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from . import config

log = logging.getLogger(__name__)

DDL = """
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE TABLE IF NOT EXISTS core.trm_diaria (
    fecha           DATE PRIMARY KEY,
    trm             DECIMAL(10, 2) NOT NULL,
    vigencia_desde  DATE NOT NULL,
    cargado_en      TIMESTAMP DEFAULT current_timestamp
);
"""


def connect(path: Path = config.WAREHOUSE_PATH) -> duckdb.DuckDBPyConnection:
    """Abre (o crea) la bodega y se asegura de que existan los esquemas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(DDL)
    return con


def last_loaded_date(con: duckdb.DuckDBPyConnection) -> date | None:
    return con.execute("SELECT max(fecha) FROM core.trm_diaria").fetchone()[0]


def upsert_daily(con: duckdb.DuckDBPyConnection, daily: pd.DataFrame) -> int:
    """Inserta o reemplaza por fecha: correrlo dos veces con los mismos datos no duplica nada."""
    if daily.empty:
        return 0
    con.register("lote_nuevo", daily)
    con.execute(
        """
        INSERT OR REPLACE INTO core.trm_diaria (fecha, trm, vigencia_desde)
        SELECT fecha, trm, vigencia_desde FROM lote_nuevo
        """
    )
    con.unregister("lote_nuevo")
    return len(daily)


def build_marts(con: duckdb.DuckDBPyConnection, sql_dir: Path = config.SQL_DIR) -> list[str]:
    """Ejecuta los modelos SQL en orden de nombre (01_, 02_, ...)."""
    built = []
    for sql_file in sorted(sql_dir.glob("*.sql")):
        con.execute(sql_file.read_text(encoding="utf-8"))
        built.append(sql_file.stem)
        log.info("Modelo construido: %s", sql_file.stem)
    return built
