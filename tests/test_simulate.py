"""Testy integracyjne orkiestracji oraz walidacja literaturowa."""

import math

import pytest

from koferymentacja import Poziom, symuluj
from koferymentacja.io_layer.schema import WynikSymulacji


def test_poziom1_pelny_wynik():
    w = symuluj({"wsad": [{"typ": "osady_mieszane", "masa_roczna_Mg": 12000}]})
    assert isinstance(w, WynikSymulacji)
    assert w.poziom == Poziom.podstawowy
    assert w.energia.CH4_Nm3 > 0
    assert w.energia.E_el_netto_kWh > 0
    # P1 nie liczy wrażliwości
    assert w.ekonomia.wrazliwosc == {}


def test_bilans_domyka_sie():
    w = symuluj({"wsad": [
        {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
        {"typ": "bio_kuchenne", "masa_roczna_Mg": 4000},
    ]})
    assert math.isclose(w.bilans_masy.domkniecie_proc, 100.0, abs_tol=0.01)
    assert math.isclose(
        w.bilans_masy.biogaz_Mg + w.poferment.masa_Mg, w.bilans_masy.wsad_Mg, rel_tol=1e-9
    )
    # implikowany rozkład s.m.o. fizyczny (<= 100%)
    assert w.bilans_masy.spojnosc_gaz_so_proc <= 100.0


def test_poziom2_liczy_wrazliwosc_i_metryki():
    w = symuluj({
        "poziom": "profesjonalny",
        "wsad": [
            {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
            {"typ": "bio_kuchenne", "masa_roczna_Mg": 6000},
        ],
    })
    assert set(w.ekonomia.wrazliwosc) == {"gate_fee", "c_el", "CAPEX", "stopa_dysk", "Y_CH4"}
    # wrażliwość symetryczna dla NPV liniowego względem Y_CH4
    yc = w.ekonomia.wrazliwosc["Y_CH4"]
    assert yc["npv_gora"] > yc["npv_dol"]
    assert w.ekonomia.NPV is not None


def test_sciezka_biometan():
    w = symuluj({
        "poziom": "profesjonalny",
        "wsad": [{"typ": "bio_mieszane", "masa_roczna_Mg": 8000}],
        "wyjscie": {"sciezka": "biometan"},
    })
    assert w.energia.biometan_Nm3 > 0
    assert w.energia.E_biometan_kWh > 0
    assert w.energia.E_el_netto_kWh is None  # brak CHP


def test_walidacja_literaturowa_y_ch4_poza_zakresem():
    # Y_CH4 = 999 dla osadów wstępnych jest poza zakresem literaturowym
    w = symuluj({"wsad": [
        {"typ": "osady_wstepne", "masa_roczna_Mg": 10000, "Y_CH4": 999},
    ]})
    assert any("Y_CH4" in o and "zakres" in o for o in w.ostrzezenia)


def test_buswell_ostrzezenie_p3():
    # Y_CH4 powyżej teorii dla glukozowego składu -> ostrzeżenie tylko na P3
    wsad = {
        "typ": "bio_kuchenne",
        "masa_roczna_Mg": 5000,
        "Y_CH4": 600,  # > ~373 teoretycznego maksimum glukozy
        "sklad_pierwiastkowy": {"C": 0.40, "H": 0.067, "O": 0.533},
    }
    w3 = symuluj({"poziom": "precyzyjny", "wsad": [wsad]})
    assert any("Buswell" in o for o in w3.ostrzezenia)
    # na P1 kontroli Buswella nie ma
    w1 = symuluj({"poziom": "podstawowy", "wsad": [wsad]})
    assert not any("Buswell" in o for o in w1.ostrzezenia)


def test_chlonnosc_p3_z_arealem():
    w = symuluj({
        "poziom": "precyzyjny",
        "wsad": [{"typ": "bio_kuchenne", "masa_roczna_Mg": 10000}],
        "poferment": {"areal_dostepny_ha": 10},
    })
    # mały areał -> nadwyżka pofermentu poza nawóz
    assert w.poferment.chlonnosc_ha_wymagana > 10
    assert w.poferment.wariant_zagospodarowania["pelet_nawozowy"] > 0


def test_pusty_wsad_odrzucony():
    with pytest.raises(Exception):
        symuluj({"wsad": []})


def test_walidacja_literaturowa_domyslne_bez_ostrzezen():
    # domyślny katalog mieści się w zakresach -> brak ostrzeżeń o zakresie
    w = symuluj({"poziom": "profesjonalny", "wsad": [
        {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
        {"typ": "bio_kuchenne", "masa_roczna_Mg": 4000},
    ]})
    assert not any("poza zakresem" in o for o in w.ostrzezenia)
