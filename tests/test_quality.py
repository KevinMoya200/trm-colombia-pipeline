from datetime import date

import pandas as pd
import pytest

from pipeline.quality import DataQualityError, check_daily, enforce


def _df(rows):
    return pd.DataFrame(rows, columns=["fecha", "trm"])


def test_datos_sanos_pasan():
    rep = check_daily(_df([(date(2025, 1, 1), 4000.0), (date(2025, 1, 2), 4010.0)]))
    assert rep.ok and not rep.warnings


def test_valor_fuera_de_rango_es_error():
    rep = check_daily(_df([(date(2025, 1, 1), 4000.0), (date(2025, 1, 2), 40.0)]))
    assert not rep.ok
    with pytest.raises(DataQualityError):
        enforce(rep)


def test_fechas_duplicadas_son_error():
    rep = check_daily(_df([(date(2025, 1, 1), 4000.0), (date(2025, 1, 1), 4001.0)]))
    assert any("duplicadas" in e for e in rep.errors)


def test_hueco_en_el_calendario_y_salto_grande_son_alertas():
    rep = check_daily(_df([(date(2025, 1, 1), 4000.0), (date(2025, 1, 5), 4800.0)]))
    assert rep.ok
    assert len(rep.warnings) == 2


def test_dato_desactualizado_es_error():
    rep = check_daily(_df([(date(2025, 1, 1), 4000.0)]), today=date(2025, 3, 1))
    assert any("antigüedad" in e for e in rep.errors)
