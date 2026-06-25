"""Konwersje jednostek — jedyne miejsce w module, w którym żonglujemy mnożnikami.

Łańcuch jednostkowy modułu: Mg/rok -> Nm3/rok -> kWh/rok -> zł/rok.

Zasada: te funkcje są czyste i nie zawierają stałych domenowych (gęstości,
wartości opałowych). Stałe pochodzą z ``data/stale.json`` i są przekazywane
przez wywołującego, aby nie dublować "magicznych liczb".
"""

from __future__ import annotations

KG_PER_MG: float = 1000.0
KWH_PER_MWH: float = 1000.0


def mg_to_kg(mass_mg: float) -> float:
    """Megagramy (tony) -> kilogramy."""
    return mass_mg * KG_PER_MG


def kg_to_mg(mass_kg: float) -> float:
    """Kilogramy -> megagramy (tony)."""
    return mass_kg / KG_PER_MG


def kwh_to_mwh(energy_kwh: float) -> float:
    """kWh -> MWh."""
    return energy_kwh / KWH_PER_MWH


def ch4_volume_from_vs_load(vs_load_mg: float, y_ch4_nl_per_kg: float) -> float:
    """Objętość metanu [Nm3/rok] z ładunku s.m.o. [Mg VS/rok].

    Sztuczka jednostkowa z wytycznych (4.2): Y_CH4 podawane jest w
    NL CH4/kg VS, a ładunek w Mg VS. Ponieważ 1 Mg = 1000 kg oraz
    1 Nm3 = 1000 NL, mnożniki 1000 się skracają i wynik wychodzi wprost
    w Nm3/rok:

        Nm3 = (Mg VS * 1000 kg/Mg) * (NL/kg) / 1000 NL/Nm3
            = Mg VS * (NL/kg)
    """
    return vs_load_mg * y_ch4_nl_per_kg


def energy_from_ch4_volume(ch4_nm3: float, wo_ch4_kwh_per_nm3: float) -> float:
    """Energia chemiczna w metanie [kWh/rok] = V_CH4 [Nm3] * Wo_CH4 [kWh/Nm3]."""
    return ch4_nm3 * wo_ch4_kwh_per_nm3


def gas_mass_mg_from_volume(volume_nm3: float, density_kg_per_nm3: float) -> float:
    """Masa gazu [Mg/rok] z objętości [Nm3/rok] i gęstości [kg/Nm3]."""
    return kg_to_mg(volume_nm3 * density_kg_per_nm3)
