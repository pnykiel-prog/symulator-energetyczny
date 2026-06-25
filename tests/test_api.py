"""Testy interfejsu web/API (FastAPI)."""

import pytest
from fastapi.testclient import TestClient

from koferymentacja.web.app import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_strona_glowna_serwuje_formularz():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Moduł koferymentacyjny" in r.text


def test_meta_zawiera_typy_i_domyslne():
    r = client.get("/api/meta")
    assert r.status_code == 200
    d = r.json()
    assert "osady_mieszane" in d["typy_substratow"]
    assert "profesjonalny" in d["poziomy"]
    assert "chp" in d["sciezki"] and "biometan" in d["sciezki"]
    assert d["ekonomia_domyslna"]["CAPEX_zl"] > 0


def test_symuluj_zwraca_pelny_wynik():
    body = {
        "poziom": "profesjonalny",
        "wsad": [
            {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
            {"typ": "bio_kuchenne", "masa_roczna_Mg": 6000},
        ],
    }
    r = client.post("/api/symuluj", json=body)
    assert r.status_code == 200
    d = r.json()
    assert d["energia"]["CH4_Nm3"] > 0
    assert d["energia"]["E_el_netto_kWh"] > 0
    assert d["ekonomia"]["NPV"] is not None
    assert abs(d["bilans_masy"]["domkniecie_proc"] - 100.0) < 0.01
    assert set(d["ekonomia"]["wrazliwosc"]) == {"gate_fee", "c_el", "CAPEX", "stopa_dysk", "Y_CH4"}


def test_symuluj_sciezka_biometan():
    body = {
        "poziom": "profesjonalny",
        "wsad": [{"typ": "bio_mieszane", "masa_roczna_Mg": 8000}],
        "wyjscie": {"sciezka": "biometan"},
    }
    d = client.post("/api/symuluj", json=body).json()
    assert d["energia"]["biometan_Nm3"] > 0
    assert d["energia"]["E_el_netto_kWh"] is None


def test_symuluj_walidacja_zwraca_422():
    # pusty wsad narusza min_length
    r = client.post("/api/symuluj", json={"wsad": []})
    assert r.status_code == 422


def test_symuluj_zly_typ_substratu_422():
    r = client.post("/api/symuluj", json={"wsad": [{"typ": "nieistnieje", "masa_roczna_Mg": 100}]})
    assert r.status_code == 422


def test_openapi_dostepne():
    assert client.get("/openapi.json").status_code == 200
