"""Orquesta el pipeline completo: extraer, transformar, validar, cargar y reportar."""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

from . import config, extract, load, quality, report, transform

log = logging.getLogger("pipeline")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline de la TRM de Colombia")
    parser.add_argument("--full-refresh", action="store_true", help="recarga toda la historia")
    parser.add_argument("--sample", action="store_true",
                        help="usa datos sintéticos locales, sin internet (bodega y salidas aparte)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    started = time.perf_counter()
    con = load.connect(config.SAMPLE_WAREHOUSE_PATH if args.sample else config.WAREHOUSE_PATH)

    if args.sample:
        records = extract.load_sample()
    else:
        since = None
        last = None if args.full_refresh else load.last_loaded_date(con)
        if last:
            since = last - timedelta(days=config.OVERLAP_DAYS)
            log.info("Carga incremental desde %s", since)
        else:
            log.info("Carga completa de la historia")
        records = extract.fetch_trm(since=since)
        raw_path = extract.save_raw(records)
        log.info("Crudo guardado en %s", raw_path.relative_to(config.ROOT))
    log.info("Extraídos %s registros", len(records))

    daily = transform.to_daily(records)
    log.info("Transformados a %s días", len(daily))
    quality.enforce(quality.check_daily(daily))

    loaded = load.upsert_daily(con, daily)
    log.info("Cargados %s días en core.trm_diaria", loaded)

    # La validación final se hace sobre toda la tabla, no solo sobre el lote nuevo
    full = con.execute("SELECT fecha, trm FROM core.trm_diaria ORDER BY fecha").df()
    quality.enforce(quality.check_daily(full, today=None if args.sample else date.today()))

    load.build_marts(con)
    outputs = report.publish(con, sample=args.sample)
    log.info("Salidas: %s", ", ".join(str(p.relative_to(config.ROOT)) for p in outputs))
    con.close()
    log.info("Listo en %.1f s", time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
