from datetime import date

import pytest

from pipeline.transform import to_daily


def _rec(valor, desde, hasta):
    return {"valor": valor, "unidad": "COP",
            "vigenciadesde": f"{desde}T00:00:00.000", "vigenciahasta": f"{hasta}T00:00:00.000"}


def test_expande_la_vigencia_de_fin_de_semana_a_un_dia_por_fila():
    df = to_daily([_rec("4000.10", "2025-01-03", "2025-01-03"),
                   _rec("4010.50", "2025-01-04", "2025-01-06")])
    assert list(df["fecha"]) == [date(2025, 1, 3), date(2025, 1, 4), date(2025, 1, 5), date(2025, 1, 6)]
    assert list(df["trm"]) == [4000.10, 4010.50, 4010.50, 4010.50]


def test_si_dos_vigencias_se_cruzan_gana_la_mas_reciente():
    df = to_daily([_rec("4000.00", "2025-01-04", "2025-01-06"),
                   _rec("4020.00", "2025-01-06", "2025-01-06")])
    assert df.loc[df["fecha"] == date(2025, 1, 6), "trm"].item() == 4020.00
    assert df["fecha"].is_unique


def test_falla_si_la_api_cambia_de_columnas():
    with pytest.raises(ValueError, match="Faltan columnas"):
        to_daily([{"valor": "4000", "fecha": "2025-01-01"}])


def test_lista_vacia_devuelve_tabla_vacia():
    df = to_daily([])
    assert df.empty
    assert list(df.columns) == ["fecha", "trm", "vigencia_desde"]
