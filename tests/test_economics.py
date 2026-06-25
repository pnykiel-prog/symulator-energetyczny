"""Testy ekonomii: CRF, NPV, IRR, LCOE i jawna obsługa dzielenia przez zero."""

import math

import pytest

from koferymentacja.core import economics
from koferymentacja.core.economics import StrumieniePrzychodow


def test_crf_recznie():
    # r=0.07, n=15 -> CRF ~ 0.10979
    assert math.isclose(economics.crf(0.07, 15), 0.07 * 1.07**15 / (1.07**15 - 1))


def test_crf_zerowa_stopa():
    assert math.isclose(economics.crf(0.0, 10), 0.1)


def test_npv_staly_cf():
    # CF=1000/rok, capex=5000, r=0.10, n=10
    npv = economics.npv_staly_cf(1000, 5000, 0.10, 10)
    annuita = 1000 * (1 - 1.10**-10) / 0.10
    assert math.isclose(npv, annuita - 5000)


def test_npv_zerowa_stopa():
    # r=0 -> NPV = CF*n - capex = 1000*10 - 5000 = 5000
    assert math.isclose(economics.npv_staly_cf(1000, 5000, 0.0, 10), 5000)


def test_irr_dodatni():
    irr = economics.irr_staly_cf(1000, 5000, 10)
    assert irr is not None and 0.10 < irr < 0.20


def test_irr_brak_capex():
    assert economics.irr_staly_cf(1000, 0, 10) is None


def test_lcoe_recznie():
    # capex 5000 * CRF + opex / produkcja
    val = economics.lcoe(5000, 100, 1000, 0.07, 15)
    oczek = (5000 * economics.crf(0.07, 15) + 100) / 1000
    assert math.isclose(val, oczek)


def test_lcoe_zerowa_produkcja_zwraca_none():
    # jawna obsługa dzielenia przez zero
    assert economics.lcoe(5000, 100, 0.0, 0.07, 15) is None


def test_metryki_zerowa_produkcja_el():
    przychody = StrumieniePrzychodow(0, 0, 0, 0, 0, 0)
    w = economics.metryki_finansowe(
        przychody, opex_rok=100, capex_zl=1000, dofinansowanie_frac=0,
        stopa_dysk=0.07, okres_lat=10, e_el_netto_kwh=0, q_th_netto_kwh=0,
    )
    assert w.LCOE is None and w.LCOH is None
    assert w.payback_lat is None  # ujemny CF


def test_dofinansowanie_obniza_capex_netto():
    przychody = StrumieniePrzychodow(1000, 0, 0, 0, 0, 0)
    w = economics.metryki_finansowe(
        przychody, 100, capex_zl=1000, dofinansowanie_frac=0.5,
        stopa_dysk=0.07, okres_lat=10, e_el_netto_kwh=100, q_th_netto_kwh=100,
    )
    assert math.isclose(w.CAPEX_netto, 500)
