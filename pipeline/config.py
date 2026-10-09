"""Configuración central del pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_PATH = DATA_DIR / "warehouse.duckdb"
SAMPLE_WAREHOUSE_PATH = DATA_DIR / "warehouse_sample.duckdb"
SQL_DIR = ROOT / "sql"
OUTPUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"
SAMPLE_FILE = ROOT / "tests" / "fixtures" / "trm_api_sintetico.json"

# TRM histórica certificada por la Superintendencia Financiera de Colombia,
# publicada en datos.gov.co (API Socrata)
DATASET_ID = "mcec-87by"
API_URL = f"https://www.datos.gov.co/resource/{DATASET_ID}.json"
PAGE_SIZE = 50_000
REQUEST_TIMEOUT = 60  # segundos
OVERLAP_DAYS = 7  # en cargas incrementales se vuelven a traer unos días por si hubo correcciones
