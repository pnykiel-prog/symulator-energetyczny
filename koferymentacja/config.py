"""Ładowanie warstwy danych (``data/*.json``) i rozwiązywanie parametrów.

Cała wiedza liczbowa (współczynniki, ceny, stałe) pochodzi stąd, nie z kodu
silnika. Konfiguracja łączy wartości domyślne z nadpisaniami z wejścia, zgodnie
z zasadą: brak danych wyższego poziomu wypełniany jest domyślną niższego.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _wczytaj(nazwa: str) -> dict:
    with open(DATA_DIR / nazwa, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Katalog:
    """Zestaw danych modułu wczytany z plików JSON."""

    substraty: dict
    proces: dict
    chp: dict
    ekonomia: dict
    stale: dict

    @classmethod
    def domyslny(cls) -> "Katalog":
        return cls(
            substraty=_wczytaj("substraty.json")["substraty"],
            proces=_wczytaj("proces.json"),
            chp=_wczytaj("chp.json"),
            ekonomia=_wczytaj("ekonomia.json"),
            stale=_wczytaj("stale.json"),
        )

    # --- stałe ---
    @property
    def Wo_CH4(self) -> float:
        return self.stale["Wo_CH4_kWh_per_Nm3"]["wartosc"]

    @property
    def limit_azotanowy(self) -> float:
        return self.stale["limit_azotanowy_kgN_per_ha_rok"]["wartosc"]

    @property
    def gestosc_biogazu(self) -> float:
        return self.stale["gestosc_biogazu_kg_per_Nm3"]["wartosc"]

    @property
    def limity_metali(self) -> dict:
        return self.stale["limity_metali_nawoz_mg_per_kg_sm"]

    @property
    def buswell(self) -> dict:
        return self.stale["buswell"]


def _wybierz(nadpisanie, domyslna):
    return domyslna if nadpisanie is None else nadpisanie


def parametry_procesu(katalog: Katalog, proces_wej) -> dict:
    """Efektywne parametry procesu: tryb -> domyślne, nadpisane wejściem."""
    tryb = proces_wej.tryb.value
    dom = katalog.proces["tryby"][tryb]
    return {
        "tryb": tryb,
        "T_C": dom["T_C"],
        "HRT_dni": _wybierz(proces_wej.HRT_dni, dom["HRT_dni"]),
        "OLR_kgVS_m3_d": _wybierz(proces_wej.OLR_kgVS_m3_d, dom["OLR_kgVS_m3_d"]),
        "eta_VS": _wybierz(proces_wej.eta_VS, dom["eta_VS"]),
        "u_frakcja_stala": katalog.proces["u_frakcja_stala"]["wartosc"],
    }


def parametry_chp(katalog: Katalog, wyjscie_wej) -> dict:
    """Efektywne sprawności CHP."""
    dom = katalog.chp["chp"]
    return {
        "eta_el": _wybierz(wyjscie_wej.eta_el, dom["eta_el"]),
        "eta_th": _wybierz(wyjscie_wej.eta_th, dom["eta_th"]),
        "e_wlasne_frac": _wybierz(wyjscie_wej.e_wlasne_frac, dom["e_wlasne_frac"]),
        "q_wlasne_frac": _wybierz(wyjscie_wej.q_wlasne_frac, dom["q_wlasne_frac"]),
    }


def parametry_biometan(katalog: Katalog, wyjscie_wej) -> dict:
    dom = katalog.chp["biometan"]
    return {
        "s_CH4_poslizg_frac": _wybierz(wyjscie_wej.s_CH4_poslizg_frac, dom["s_CH4_poslizg_frac"]),
        "energia_wlasna_kWh_per_Nm3_biogazu": dom["energia_wlasna_kWh_per_Nm3_biogazu"],
    }


def _tylko_liczby(d: dict) -> dict:
    """Odfiltrowuje pola metadanych (np. 'źródło') zostawiając wartości liczbowe."""
    return {k: v for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def parametry_ekonomiczne(katalog: Katalog, ekon_wej) -> dict:
    """Efektywne parametry ekonomiczne: domyślne z ekonomia.json, nadpisane wejściem."""
    dom = katalog.ekonomia
    inwest = dom["inwestycja"]
    return {
        "gate_fee_per_typ": _wybierz(ekon_wej.gate_fee_per_typ, _tylko_liczby(dom["gate_fee_zl_per_Mg"])),
        "ceny": _wybierz(ekon_wej.ceny, _tylko_liczby(dom["ceny"])),
        "CAPEX_zl": _wybierz(ekon_wej.CAPEX_zl, inwest["CAPEX_zl"]),
        "OPEX_zl_rok": _wybierz(ekon_wej.OPEX_zl_rok, inwest["OPEX_zl_rok"]),
        "stopa_dysk": _wybierz(ekon_wej.stopa_dysk, inwest["stopa_dysk"]),
        "okres_lat": _wybierz(ekon_wej.okres_lat, inwest["okres_lat"]),
        "dofinansowanie_frac": _wybierz(ekon_wej.dofinansowanie_frac, inwest["dofinansowanie_frac"]),
    }
