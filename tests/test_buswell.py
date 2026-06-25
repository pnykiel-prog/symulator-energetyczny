"""Test kontroli teoretycznej Buswella (P3)."""

import math

from koferymentacja.config import Katalog
from koferymentacja.core import digestion


def _stale():
    k = Katalog.domyslny()
    bus = k.buswell
    return bus["masy_molowe_kg_per_kmol"], bus["objetosc_molowa_Nm3_per_kmol"]["wartosc"]


def test_buswell_glukoza():
    # glukoza C6H12O6: 3 mol CH4 / mol -> ~373 NL CH4/kg VS
    masy, vm = _stale()
    sklad = {"C": 72 / 180, "H": 12 / 180, "O": 96 / 180}
    y_max = digestion.buswell_max_y_ch4(sklad, masy, vm)
    assert math.isclose(y_max, 373.0, rel_tol=0.02)


def test_buswell_brak_ujemnych():
    # skrajnie utleniony skład nie może dać ujemnego uzysku
    masy, vm = _stale()
    y = digestion.buswell_max_y_ch4({"O": 1.0}, masy, vm)
    assert y == 0.0


def test_buswell_tluszcz_wiekszy_niz_cukier():
    # lipidy (więcej H, mniej O) -> wyższy teoretyczny uzysk niż cukry
    masy, vm = _stale()
    cukier = digestion.buswell_max_y_ch4({"C": 0.40, "H": 0.067, "O": 0.533}, masy, vm)
    tluszcz = digestion.buswell_max_y_ch4({"C": 0.77, "H": 0.12, "O": 0.11}, masy, vm)
    assert tluszcz > cukier
