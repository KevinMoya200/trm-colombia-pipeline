"""Extracción: descarga la TRM desde la API de datos.gov.co."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

log = logging.getLogger(__name__)


def _session() -> requests.Session:
    """Sesión HTTP con reintentos y espera exponencial ante errores temporales."""
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Accept": "application/json", "User-Agent": "trm-colombia-pipeline"})
    return session


def fetch_trm(since: date | None = None, page_size: int = config.PAGE_SIZE) -> list[dict]:
    """Trae los registros de la API paginando con $limit y $offset.

    Si se pasa `since`, solo pide las vigencias que empiezan desde esa fecha
    (carga incremental). Sin `since`, trae toda la historia.
    """
    session = _session()
    records: list[dict] = []
    offset = 0
    while True:
        params = {"$order": "vigenciadesde ASC", "$limit": page_size, "$offset": offset}
        if since:
            params["$where"] = f"vigenciadesde >= '{since.isoformat()}T00:00:00.000'"
        response = session.get(config.API_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        page = response.json()
        records.extend(page)
        log.info("Página con offset %s: %s registros", offset, len(page))
        if len(page) < page_size:
            break
        offset += page_size
    return records


def load_sample(path: Path = config.SAMPLE_FILE) -> list[dict]:
    """Lee un archivo local con el mismo formato de la API (modo sin internet)."""
    return json.loads(path.read_text(encoding="utf-8"))


def save_raw(records: list[dict], raw_dir: Path = config.RAW_DIR) -> Path:
    """Guarda la respuesta tal cual llegó (capa cruda), para poder reprocesar sin volver a la API."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = raw_dir / f"trm_{stamp}.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path
