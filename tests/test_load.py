from pipeline import config, extract, load, transform


def test_el_upsert_es_idempotente(tmp_path):
    con = load.connect(tmp_path / "test.duckdb")
    daily = transform.to_daily(extract.load_sample())
    load.upsert_daily(con, daily)
    load.upsert_daily(con, daily)
    total = con.execute("SELECT count(*) FROM core.trm_diaria").fetchone()[0]
    assert total == len(daily)


def test_los_modelos_sql_se_construyen(tmp_path):
    con = load.connect(tmp_path / "test.duckdb")
    load.upsert_daily(con, transform.to_daily(extract.load_sample()))
    built = load.build_marts(con, config.SQL_DIR)
    assert built == ["01_mart_trm_mensual", "02_mart_trm_volatilidad", "03_mart_trm_resumen"]
    meses = con.execute("SELECT count(*) FROM marts.trm_mensual").fetchone()[0]
    assert meses == 6
    resumen = con.execute("SELECT trm_actual, dias_en_bodega FROM marts.trm_resumen").fetchone()
    assert resumen[0] > 0 and resumen[1] > 150
