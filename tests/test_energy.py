"""Testy konwersji energii (CHP i biometan)."""

import math

import pytest

from koferymentacja.core import energy


def test_chp_recznie():
    # E_CH4 = 1 000 000 kWh ; eta_el 0.40, eta_th 0.43 ; e_wł 0.08, q_wł 0.25
    w = energy.chp(1_000_000, 0.40, 0.43, 0.08, 0.25)
    assert math.isclose(w.E_el_brutto_kWh, 400_000)
    assert math.isclose(w.Q_th_brutto_kWh, 430_000)
    assert math.isclose(w.E_el_netto_kWh, 400_000 * 0.92)
    assert math.isclose(w.Q_th_netto_kWh, 430_000 * 0.75)


def test_chp_walidacja():
    with pytest.raises(ValueError):
        energy.chp(1000, 1.5, 0.4, 0.08, 0.25)
    with pytest.raises(ValueError):
        energy.chp(1000, 0.4, 0.4, 1.2, 0.25)


def test_biometan_recznie():
    # V_CH4 = 100 000 Nm3 ; poślizg 0.02 -> 98 000 Nm3 biometanu
    w = energy.biometan(100_000, 160_000, 0.02, 9.97, 0.30)
    assert math.isclose(w.V_biometan_Nm3, 98_000)
    assert math.isclose(w.E_biometan_kWh, 98_000 * 9.97)
    assert math.isclose(w.E_pomocnicza_kWh, 160_000 * 0.30)


def test_biometan_walidacja():
    with pytest.raises(ValueError):
        energy.biometan(1000, 1600, 1.5, 9.97)
