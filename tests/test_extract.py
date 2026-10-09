from datetime import date

from pipeline import extract


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_pagina_hasta_que_la_api_devuelve_menos_que_el_limite(monkeypatch):
    calls = []
    pages = [[{"valor": "1"}] * 3, [{"valor": "2"}] * 3, [{"valor": "3"}]]

    def fake_get(self, url, params, timeout):
        calls.append(params.copy())
        return _FakeResponse(pages[len(calls) - 1])

    monkeypatch.setattr("requests.Session.get", fake_get)
    records = extract.fetch_trm(page_size=3)
    assert len(records) == 7
    assert [c["$offset"] for c in calls] == [0, 3, 6]


def test_carga_incremental_filtra_por_fecha(monkeypatch):
    seen = {}

    def fake_get(self, url, params, timeout):
        seen.update(params)
        return _FakeResponse([])

    monkeypatch.setattr("requests.Session.get", fake_get)
    extract.fetch_trm(since=date(2026, 10, 1))
    assert seen["$where"] == "vigenciadesde >= '2026-10-01T00:00:00.000'"
