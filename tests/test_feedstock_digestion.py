"""Testy wsadu i fermentacji z ręcznie policzonymi przypadkami."""

import math

import pytest

from koferymentacja.config import Katalog
from koferymentacja.core import digestion
from koferymentacja.core.feedstock import vs_load, zbuduj_mieszanke
from koferymentacja.io_layer.schema import WsadSubstrat


@pytest.fixture
def katalog():
    return Katalog.domyslny()


def test_vs_load_recznie():
    # 10 000 Mg * 0,05 * 0,75 = 375 Mg VS
    assert math.isclose(vs_load(10000, 0.05, 0.75), 375.0)


def test_mieszanka_agreguje_mase_i_vs(katalog):
    wsad = [
        WsadSubstrat(typ="osady_wstepne", masa_roczna_Mg=10000),
        WsadSubstrat(typ="bio_kuchenne", masa_roczna_Mg=2000),
    ]
    mieszanka, _ = zbuduj_mieszanke(wsad, katalog.substraty)
    # osady: 10000*0.05*0.75=375 ; bio: 2000*0.28*0.90=504
    assert math.isclose(mieszanka.vs_load_calkowity_Mg, 375 + 504)
    assert mieszanka.masa_calkowita_Mg == 12000
    assert math.isclose(mieszanka.proporcje_masowe["osady_wstepne"], 10000 / 12000)


def test_pomiar_nadpisuje_tablice(katalog):
    wsad = [WsadSubstrat(typ="osady_wstepne", masa_roczna_Mg=10000, TS_frac=0.06, VS_frac=0.80, Y_CH4=300)]
    mieszanka, _ = zbuduj_mieszanke(wsad, katalog.substraty)
    s = mieszanka.substraty[0]
    assert s.TS_frac == 0.06 and s.VS_frac == 0.80 and s.Y_CH4 == 300
    assert s.zrodlo_pomiarowe["Y_CH4"] is True
    assert s.zrodlo_pomiarowe["f_CH4"] is False  # nie podano -> tablica


def test_metan_recznie(katalog):
    # 1 substrat: 100 Mg masa, TS 0.05, VS 0.75 -> 3.75 Mg VS ; Y=350 -> 1312.5 Nm3 CH4
    wsad = [WsadSubstrat(typ="osady_wstepne", masa_roczna_Mg=100, TS_frac=0.05, VS_frac=0.75, Y_CH4=350, f_CH4=0.65)]
    mieszanka, _ = zbuduj_mieszanke(wsad, katalog.substraty)
    ferment = digestion.fermentuj(mieszanka, eta_vs=0.5, wo_ch4_kwh_per_nm3=9.97)
    assert math.isclose(ferment.V_CH4_Nm3, 3.75 * 350)
    # biogaz = CH4 / f_CH4
    assert math.isclose(ferment.V_biogaz_Nm3, (3.75 * 350) / 0.65)
    # E_CH4 = V_CH4 * 9,97
    assert math.isclose(ferment.E_CH4_kWh, 3.75 * 350 * 9.97)
    # VS destroyed = 3.75 * 0.5
    assert math.isclose(ferment.vs_destroyed_Mg, 3.75 * 0.5)


def test_eta_vs_zakres():
    from koferymentacja.core.digestion import vs_rozlozone
    from koferymentacja.core.feedstock import Mieszanka

    m = Mieszanka([], 0, 100, 0.6, {})
    with pytest.raises(ValueError):
        vs_rozlozone(m, 1.5)


def test_przefermentowane_uzysk_bliski_zeru(katalog):
    # przypadek brzegowy: osady przefermentowane -> uzysk metanu bliski zeru
    wsad = [WsadSubstrat(typ="osady_przefermentowane", masa_roczna_Mg=10000)]
    mieszanka, _ = zbuduj_mieszanke(wsad, katalog.substraty)
    ferment = digestion.fermentuj(mieszanka, 0.5, 9.97)
    # Y_CH4 tablicowe = 30 NL/kg, VS = 10000*0.03*0.60=180 Mg -> 5400 Nm3 (mało)
    uzysk_na_Mg_wsadu = ferment.V_CH4_Nm3 / mieszanka.masa_calkowita_Mg
    assert uzysk_na_Mg_wsadu < 1.0  # < 1 Nm3 CH4 na Mg wsadu


def test_zerowy_strumien(katalog):
    wsad = [WsadSubstrat(typ="osady_mieszane", masa_roczna_Mg=0)]
    mieszanka, ostrz = zbuduj_mieszanke(wsad, katalog.substraty)
    ferment = digestion.fermentuj(mieszanka, 0.5, 9.97)
    assert ferment.V_CH4_Nm3 == 0
    assert ferment.V_biogaz_Nm3 == 0  # brak dzielenia przez zero
