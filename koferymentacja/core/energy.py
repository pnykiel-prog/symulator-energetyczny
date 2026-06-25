"""Konwersja energii: ścieżka CHP (kogeneracja) lub biometan.

Implementuje równania 4.4a (CHP) i 4.4b (biometan). Potrzeby własne instalacji
odejmowane są od produkcji brutto, dając eksport netto.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import units


@dataclass(frozen=True)
class WynikEnergiaCHP:
    E_el_brutto_kWh: float
    E_el_netto_kWh: float
    Q_th_brutto_kWh: float
    Q_th_netto_kWh: float


@dataclass(frozen=True)
class WynikEnergiaBiometan:
    V_biometan_Nm3: float
    E_biometan_kWh: float
    E_pomocnicza_kWh: float  # energia zużyta na uszlachetnianie


def chp(
    e_ch4_kwh: float,
    eta_el: float,
    eta_th: float,
    e_wlasne_frac: float,
    q_wlasne_frac: float,
) -> WynikEnergiaCHP:
    """Ścieżka kogeneracji (4.4a).

    E_el_brutto = E_CH4 * η_el; Q_th_brutto = E_CH4 * η_th.
    Netto = brutto * (1 - potrzeby własne).
    """
    for nazwa, v in (("η_el", eta_el), ("η_th", eta_th)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{nazwa} musi być w [0,1], otrzymano {v}")
    for nazwa, v in (("e_wł", e_wlasne_frac), ("q_wł", q_wlasne_frac)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{nazwa} musi być w [0,1], otrzymano {v}")

    e_el_brutto = e_ch4_kwh * eta_el
    q_th_brutto = e_ch4_kwh * eta_th
    e_el_netto = e_el_brutto * (1.0 - e_wlasne_frac)
    q_th_netto = q_th_brutto * (1.0 - q_wlasne_frac)

    return WynikEnergiaCHP(
        E_el_brutto_kWh=e_el_brutto,
        E_el_netto_kWh=e_el_netto,
        Q_th_brutto_kWh=q_th_brutto,
        Q_th_netto_kWh=q_th_netto,
    )


def biometan(
    v_ch4_nm3: float,
    v_biogaz_nm3: float,
    s_ch4_poslizg_frac: float,
    wo_ch4_kwh_per_nm3: float,
    energia_wlasna_kwh_per_nm3_biogazu: float = 0.0,
) -> WynikEnergiaBiometan:
    """Ścieżka biometanu (4.4b).

    V_biometan = V_CH4 * (1 - s_CH4) [poślizg metanu];
    E_biometan = V_biometan * Wo_CH4.
    Energia pomocnicza na uszlachetnianie liczona od objętości biogazu.
    """
    if not 0.0 <= s_ch4_poslizg_frac <= 1.0:
        raise ValueError(f"s_CH4 musi być w [0,1], otrzymano {s_ch4_poslizg_frac}")

    v_biometan = v_ch4_nm3 * (1.0 - s_ch4_poslizg_frac)
    e_biometan = units.energy_from_ch4_volume(v_biometan, wo_ch4_kwh_per_nm3)
    e_pomoc = v_biogaz_nm3 * energia_wlasna_kwh_per_nm3_biogazu

    return WynikEnergiaBiometan(
        V_biometan_Nm3=v_biometan,
        E_biometan_kWh=e_biometan,
        E_pomocnicza_kWh=e_pomoc,
    )
