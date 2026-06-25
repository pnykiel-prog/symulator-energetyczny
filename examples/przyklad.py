"""Przykład użycia modułu koferymentacyjnego — trzy poziomy wierności.

Uruchom:  python examples/przyklad.py
"""

from __future__ import annotations

import json

from koferymentacja import symuluj


def pokaz(tytul: str, wejscie: dict) -> None:
    print(f"\n{'=' * 70}\n{tytul}\n{'=' * 70}")
    wynik = symuluj(wejscie)
    e, p, ek, b = wynik.energia, wynik.poferment, wynik.ekonomia, wynik.bilans_masy
    print(f"  Biogaz:        {e.biogaz_Nm3:>14,.0f} Nm3/rok")
    print(f"  Metan (CH4):   {e.CH4_Nm3:>14,.0f} Nm3/rok")
    if e.E_el_netto_kWh is not None:
        print(f"  En. el. netto: {e.E_el_netto_kWh / 1000:>14,.0f} MWh/rok")
        print(f"  Ciepło netto:  {e.Q_th_netto_kWh / 1000:>14,.0f} MWh/rok")
    if e.E_biometan_kWh is not None:
        print(f"  Biometan:      {e.biometan_Nm3:>14,.0f} Nm3/rok ({e.E_biometan_kWh / 1000:,.0f} MWh)")
    print(f"  Poferment:     {p.masa_Mg:>14,.0f} Mg/rok (wariant: {p.wariant_glowny})")
    print(f"  Bilans masy:   domknięcie {b.domkniecie_proc:.1f}%, rozkład s.m.o. {b.spojnosc_gaz_so_proc:.0f}%")
    print(f"  NPV:           {ek.NPV:>14,.0f} zł")
    print(f"  IRR:           {('%.1f%%' % (ek.IRR * 100)) if ek.IRR is not None else 'n/d':>14}")
    print(f"  LCOE:          {('%.3f zł/kWh' % ek.LCOE) if ek.LCOE is not None else 'n/d':>14}")
    if wynik.ostrzezenia:
        print("  Ostrzeżenia:")
        for o in wynik.ostrzezenia:
            print(f"    - {o}")


if __name__ == "__main__":
    # Poziom 1 — tylko masy i typy strumieni
    pokaz("POZIOM 1 — Podstawowy (MVP)", {
        "poziom": "podstawowy",
        "wsad": [
            {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
            {"typ": "bio_kuchenne", "masa_roczna_Mg": 4000},
        ],
    })

    # Poziom 2 — zmierzone właściwości, realne sprawności, pełna ekonomia + wrażliwość
    pokaz("POZIOM 2 — Profesjonalny", {
        "poziom": "profesjonalny",
        "wsad": [
            {"typ": "osady_mieszane", "masa_roczna_Mg": 12000, "TS_frac": 0.05, "VS_frac": 0.74},
            {"typ": "bio_kuchenne", "masa_roczna_Mg": 6000, "Y_CH4": 470},
        ],
        "proces": {"tryb": "mezofilny", "eta_VS": 0.55},
        "ekonomia": {"CAPEX_zl": 22000000, "dofinansowanie_frac": 0.4},
    })

    # Poziom 3 — BMP, kontrola Buswella, model chłonności rolniczej
    pokaz("POZIOM 3 — Precyzyjny (z chłonnością rolniczą)", {
        "poziom": "precyzyjny",
        "wsad": [
            {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
            {
                "typ": "bio_kuchenne",
                "masa_roczna_Mg": 6000,
                "BMP": 460,
                "sklad_pierwiastkowy": {"C": 0.50, "H": 0.07, "O": 0.34, "N": 0.03},
                "metale_ciezkie": {"Cd": 1.2, "Pb": 40, "Hg": 0.5},
            },
        ],
        "poferment": {"areal_dostepny_ha": 80},
    })
