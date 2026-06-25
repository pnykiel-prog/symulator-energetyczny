"""Ekonomia: przychody, koszty, NPV/IRR/LCOE/LCOH, payback (4.6).

Czyste funkcje. Analiza wrażliwości jest orkiestrowana w ``simulate.py``
(wymaga ponownego przeliczenia łańcucha dla parametrów typu Y_CH4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy_financial as npf


@dataclass(frozen=True)
class StrumieniePrzychodow:
    gate_fee: float
    energia_el: float
    cieplo: float
    biometan: float
    poferment: float
    skladowanie_unikniete: float

    def suma(self) -> float:
        return (
            self.gate_fee
            + self.energia_el
            + self.cieplo
            + self.biometan
            + self.poferment
            + self.skladowanie_unikniete
        )


@dataclass(frozen=True)
class WynikEkonomiczny:
    przychody_roczne: float
    koszty_roczne: float
    CF_rok: float
    CAPEX_netto: float
    NPV: float
    IRR: float | None
    LCOE: float | None
    LCOH: float | None
    payback_lat: float | None
    rozbicie_przychodow: StrumieniePrzychodow
    ostrzezenia: list[str] = field(default_factory=list)


def przychody_roczne(
    masy_per_typ: dict[str, float],
    gate_fee_per_typ: dict[str, float],
    e_el_netto_kwh: float,
    q_th_netto_kwh: float,
    e_biometan_kwh: float,
    masa_poferment_Mg: float,
    pozostalosci_Mg: float,
    ceny: dict,
) -> StrumieniePrzychodow:
    """Roczne przychody (4.6)."""
    gate = sum(masy_per_typ.get(t, 0.0) * gate_fee_per_typ.get(t, 0.0) for t in masy_per_typ)
    return StrumieniePrzychodow(
        gate_fee=gate,
        energia_el=e_el_netto_kwh * ceny["c_el_zl_per_kWh"],
        cieplo=q_th_netto_kwh * ceny["c_th_zl_per_kWh"],
        biometan=e_biometan_kwh * ceny["c_bm_zl_per_kWh"],
        poferment=masa_poferment_Mg * ceny["c_POF_zl_per_Mg"],
        skladowanie_unikniete=pozostalosci_Mg * ceny.get("c_skladowanie_unikniete_zl_per_Mg", 0.0),
    )


def crf(stopa_dysk: float, okres_lat: int) -> float:
    """Współczynnik annuitetowy (Capital Recovery Factor)."""
    r, n = stopa_dysk, okres_lat
    if n <= 0:
        raise ValueError("Okres musi być dodatni")
    if r == 0:
        return 1.0 / n
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def npv_staly_cf(cf_rok: float, capex_netto: float, stopa_dysk: float, okres_lat: int) -> float:
    """NPV przy stałym przepływie rocznym (4.6)."""
    r, n = stopa_dysk, okres_lat
    if r == 0:
        wartosc_biezaca = cf_rok * n
    else:
        wartosc_biezaca = cf_rok * (1 - (1 + r) ** (-n)) / r
    return wartosc_biezaca - capex_netto


def irr_staly_cf(cf_rok: float, capex_netto: float, okres_lat: int) -> float | None:
    """IRR dla przepływów [-CAPEX_netto, CF, CF, ...]."""
    if capex_netto <= 0:
        return None
    przeplywy = [-capex_netto] + [cf_rok] * okres_lat
    try:
        wynik = npf.irr(przeplywy)
    except Exception:
        return None
    if wynik is None or (isinstance(wynik, float) and math.isnan(wynik)):
        return None
    return float(wynik)


def lcoe(capex_netto: float, opex_rok: float, produkcja_kwh: float, stopa_dysk: float, okres_lat: int) -> float | None:
    """Uśredniony koszt jednostkowy energii (LCOE/LCOH).

    (annualizowany CAPEX + OPEX) / produkcja roczna. Przy zerowej produkcji
    zwraca None (jawna obsługa dzielenia przez zero).
    """
    if produkcja_kwh <= 0:
        return None
    annualizowany = capex_netto * crf(stopa_dysk, okres_lat) + opex_rok
    return annualizowany / produkcja_kwh


def metryki_finansowe(
    przychody: StrumieniePrzychodow,
    opex_rok: float,
    capex_zl: float,
    dofinansowanie_frac: float,
    stopa_dysk: float,
    okres_lat: int,
    e_el_netto_kwh: float,
    q_th_netto_kwh: float,
) -> WynikEkonomiczny:
    """Składa pełny wynik ekonomiczny."""
    ostrzezenia: list[str] = []
    r_rok = przychody.suma()
    cf_rok = r_rok - opex_rok
    capex_netto = capex_zl * (1 - dofinansowanie_frac)

    npv = npv_staly_cf(cf_rok, capex_netto, stopa_dysk, okres_lat)
    irr = irr_staly_cf(cf_rok, capex_netto, okres_lat)
    if irr is None and capex_netto > 0:
        ostrzezenia.append("Nie udało się wyznaczyć IRR (prawdopodobnie ujemne przepływy).")

    lcoe_val = lcoe(capex_netto, opex_rok, e_el_netto_kwh, stopa_dysk, okres_lat)
    lcoh_val = lcoe(capex_netto, opex_rok, q_th_netto_kwh, stopa_dysk, okres_lat)

    if cf_rok > 0:
        payback = capex_netto / cf_rok
    else:
        payback = None
        ostrzezenia.append("Niedodatni przepływ roczny — payback nieokreślony.")

    return WynikEkonomiczny(
        przychody_roczne=r_rok,
        koszty_roczne=opex_rok,
        CF_rok=cf_rok,
        CAPEX_netto=capex_netto,
        NPV=npv,
        IRR=irr,
        LCOE=lcoe_val,
        LCOH=lcoh_val,
        payback_lat=payback,
        rozbicie_przychodow=przychody,
        ostrzezenia=ostrzezenia,
    )
