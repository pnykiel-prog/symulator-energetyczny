"""Testy pofermentu: bilans masy, NPK, status nawozowy, chłonność rolnicza."""

import math

import pytest

from koferymentacja.config import Katalog
from koferymentacja.core import digestate
from koferymentacja.core.feedstock import zbuduj_mieszanke
from koferymentacja.io_layer.schema import WsadSubstrat


@pytest.fixture
def katalog():
    return Katalog.domyslny()


def test_bilans_masy_domkniecie():
    # masa biogazu z CH4+CO2 ; reszta to poferment -> domknięcie 100%
    b = digestate.bilans_masy(
        masa_wsadu_Mg=10000,
        v_ch4_Nm3=500_000,
        v_biogaz_Nm3=800_000,
        vs_load_calkowity_Mg=900,
        eta_vs=0.5,
        gestosc_CH4=0.717,
        gestosc_CO2=1.977,
        u_frakcja_stala=0.25,
    )
    assert math.isclose(b.domkniecie_proc, 100.0)
    assert math.isclose(b.biogaz_Mg + b.poferment_Mg, 10000)
    # frakcja stała + ciekła = poferment
    assert math.isclose(b.frakcja_stala_Mg + b.frakcja_ciekla_Mg, b.poferment_Mg)
    # masa biogazu = (500000*0.717 + 300000*1.977)/1000
    assert math.isclose(b.biogaz_Mg, (500_000 * 0.717 + 300_000 * 1.977) / 1000)


def test_bilans_gaz_nie_przekracza_wsadu():
    b = digestate.bilans_masy(100, 5_000_000, 8_000_000, 50, 0.5, 0.717, 1.977, 0.25)
    assert b.biogaz_Mg <= 100
    assert b.poferment_Mg >= 0


def test_npk_konserwacja(katalog):
    wsad = [WsadSubstrat(typ="bio_kuchenne", masa_roczna_Mg=1000)]
    mieszanka, _ = zbuduj_mieszanke(wsad, katalog.substraty)
    npk = digestate.npk_pofermentu(mieszanka)
    # bio_kuchenne N=5.5 kg/Mg -> 5500 kg/rok
    assert math.isclose(npk["N"], 1000 * 5.5)
    assert math.isclose(npk["K"], 1000 * 3.0)


def test_status_brak_danych(katalog):
    status, ostrz = digestate.status_nawozowy(None, 0.05, katalog.limity_metali)
    assert status == "nieokreslony_brak_danych"
    assert ostrz == []


def test_status_przekroczenie_metali(katalog):
    status, ostrz = digestate.status_nawozowy({"Cd": 10}, 0.05, katalog.limity_metali)
    assert status == "nienawozowy_przekroczone_metale"
    assert ostrz


def test_status_w_normie(katalog):
    status, _ = digestate.status_nawozowy({"Cd": 1, "Pb": 50}, 0.05, katalog.limity_metali)
    assert status == "nawozowy"


def test_chlonnosc_wystarczajacy_areal():
    npk = {"N": 17000, "P": 0, "K": 0}  # wymaga 100 ha przy limicie 170
    chl, wariant, glowny, _ = digestate.chlonnosc_rolnicza(
        npk, poferment_Mg=5000, limit_azotanowy_kgN_per_ha=170,
        areal_dostepny_ha=150, status="nawozowy",
    )
    assert math.isclose(chl, 100.0)
    assert glowny == "nawoz"
    assert math.isclose(wariant["nawoz"], 5000)


def test_chlonnosc_niewystarczajacy_areal_pelet_nawozowy():
    npk = {"N": 17000}
    chl, wariant, glowny, ostrz = digestate.chlonnosc_rolnicza(
        npk, poferment_Mg=5000, limit_azotanowy_kgN_per_ha=170,
        areal_dostepny_ha=50, status="nawozowy",
    )
    # tylko 50/100 areału -> połowa na pole, reszta pelet nawozowy
    assert math.isclose(wariant["nawoz"], 2500)
    assert math.isclose(wariant["pelet_nawozowy"], 2500)
    assert "pelet_nawozowy" in glowny
    assert ostrz


def test_chlonnosc_nienawozowy_pelet_palny():
    npk = {"N": 17000}
    _, wariant, glowny, _ = digestate.chlonnosc_rolnicza(
        npk, poferment_Mg=5000, limit_azotanowy_kgN_per_ha=170,
        areal_dostepny_ha=1000, status="nienawozowy_przekroczone_metale",
    )
    assert glowny == "pelet_palny"
    assert math.isclose(wariant["pelet_palny"], 5000)
