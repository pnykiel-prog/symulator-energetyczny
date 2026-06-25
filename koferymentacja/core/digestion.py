"""Silnik fermentacji: wsad -> biogaz -> metan -> energia chemiczna.

Implementuje równania 4.2, 4.3 i 4.5 z wytycznych. Czyste funkcje na
charakterystykach z ``feedstock.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import units
from .feedstock import Mieszanka


@dataclass(frozen=True)
class WynikFermentacji:
    V_CH4_Nm3: float           # objętość metanu [Nm3/rok]
    V_biogaz_Nm3: float        # objętość biogazu [Nm3/rok]
    E_CH4_kWh: float           # energia chemiczna w metanie [kWh/rok]
    vs_destroyed_Mg: float     # rozłożona s.m.o. [Mg VS/rok]
    V_CH4_per_substrat: dict[str, float]


def metan_z_mieszanki(mieszanka: Mieszanka) -> dict[str, float]:
    """Objętość metanu per substrat (4.2): V_CH4_i = VS_load_i * Y_CH4_i."""
    return {
        s.typ: units.ch4_volume_from_vs_load(s.vs_load_Mg, s.Y_CH4)
        for s in mieszanka.substraty
    }


def vs_rozlozone(mieszanka: Mieszanka, eta_vs: float) -> float:
    """Rozłożona s.m.o. (4.5): VS_destroyed = Σ VS_load_i * η_VS."""
    if not 0.0 <= eta_vs <= 1.0:
        raise ValueError(f"η_VS musi być w [0,1], otrzymano {eta_vs}")
    return mieszanka.vs_load_calkowity_Mg * eta_vs


def buswell_max_y_ch4(
    sklad_masowy_frac: dict[str, float],
    masy_molowe: dict[str, float],
    objetosc_molowa_Nm3_per_kmol: float,
) -> float:
    """Teoretyczny maksymalny uzysk CH4 [NL CH4/kg s.m.o.] wg równania Buswella.

    Wejście: udziały masowe pierwiastków w s.m.o. (C, H, O, N, S; suma <= 1,
    reszta to popiół). Z równania Buswella mole CH4 na 1 kg s.m.o.:

        CH4 = n/2 + a/8 - b/4 - 3c/8 - d/4

    gdzie n,a,b,c,d to liczby moli C,H,O,N,S w 1 kg s.m.o.
    Objętość: mole CH4 * 22,414 L/mol = NL CH4 / kg.
    """
    # mole pierwiastków w 1 kg (1000 g) s.m.o.
    n = sklad_masowy_frac.get("C", 0.0) * 1000.0 / masy_molowe["C"]
    a = sklad_masowy_frac.get("H", 0.0) * 1000.0 / masy_molowe["H"]
    b = sklad_masowy_frac.get("O", 0.0) * 1000.0 / masy_molowe["O"]
    c = sklad_masowy_frac.get("N", 0.0) * 1000.0 / masy_molowe["N"]
    d = sklad_masowy_frac.get("S", 0.0) * 1000.0 / masy_molowe["S"]

    ch4_mol = n / 2 + a / 8 - b / 4 - 3 * c / 8 - d / 4
    if ch4_mol < 0:
        ch4_mol = 0.0
    # 22,414 L/kmol == 22,414 NL/kmol; mole * (Nm3/kmol) daje L bo skala 1:1000 znika
    return ch4_mol * objetosc_molowa_Nm3_per_kmol


def fermentuj(
    mieszanka: Mieszanka,
    eta_vs: float,
    wo_ch4_kwh_per_nm3: float,
) -> WynikFermentacji:
    """Pełny krok fermentacji dla mieszanki.

    V_biogaz = V_CH4 / f_CH4_śr (4.2); E_CH4 = V_CH4 * Wo_CH4 (4.3).
    """
    v_ch4_per = metan_z_mieszanki(mieszanka)
    v_ch4 = sum(v_ch4_per.values())

    f_sredni = mieszanka.f_CH4_sredni
    v_biogaz = v_ch4 / f_sredni if f_sredni > 0 else 0.0

    e_ch4 = units.energy_from_ch4_volume(v_ch4, wo_ch4_kwh_per_nm3)
    vs_dest = vs_rozlozone(mieszanka, eta_vs)

    return WynikFermentacji(
        V_CH4_Nm3=v_ch4,
        V_biogaz_Nm3=v_biogaz,
        E_CH4_kWh=e_ch4,
        vs_destroyed_Mg=vs_dest,
        V_CH4_per_substrat=v_ch4_per,
    )
