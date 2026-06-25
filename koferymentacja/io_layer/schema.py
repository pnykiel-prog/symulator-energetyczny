"""Walidowane modele wejścia i wyjścia (pydantic).

Jeden model danych dla wszystkich poziomów: pola wyższych poziomów są
opcjonalne, a ich brak jest uzupełniany wartościami domyślnymi z ``data/*``.
Poziom jest atrybutem konfiguracji wejścia, nie osobnym programem.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Poziom(str, Enum):
    podstawowy = "podstawowy"
    profesjonalny = "profesjonalny"
    precyzyjny = "precyzyjny"


class TypSubstratu(str, Enum):
    osady_wstepne = "osady_wstepne"
    osady_nadmierne = "osady_nadmierne"
    osady_mieszane = "osady_mieszane"
    osady_przefermentowane = "osady_przefermentowane"
    bio_kuchenne = "bio_kuchenne"
    bio_zielone = "bio_zielone"
    bio_mieszane = "bio_mieszane"


class TrybProcesu(str, Enum):
    mezofilny = "mezofilny"
    termofilny = "termofilny"


class SciezkaWyjscia(str, Enum):
    chp = "chp"
    biometan = "biometan"


# --------------------------------------------------------------------------- #
# Wejście
# --------------------------------------------------------------------------- #


class WsadSubstrat(BaseModel):
    typ: TypSubstratu
    masa_roczna_Mg: float = Field(ge=0, description="P1: masa roczna strumienia [Mg/rok]")
    # P2/P3 — opcjonalne pomiary nadpisujące wartości tablicowe
    TS_frac: float | None = Field(default=None, gt=0, le=1, description="P2: udział suchej masy")
    VS_frac: float | None = Field(default=None, gt=0, le=1, description="P2: udział s.m.o. w s.m.")
    Y_CH4: float | None = Field(default=None, ge=0, description="P2/P3: uzysk CH4 [NL/kg VS]")
    f_CH4: float | None = Field(default=None, gt=0, le=1, description="P2: udział CH4 w biogazie")
    BMP: float | None = Field(default=None, ge=0, description="P3: uzysk z testu BMP [NL/kg VS]")
    sklad_pierwiastkowy: dict[str, float] | None = Field(
        default=None, description="P3: udziały masowe C,H,O,N,S w s.m.o. (kontrola Buswella)"
    )
    metale_ciezkie: dict[str, float] | None = Field(
        default=None, description="P3: zawartość metali ciężkich [mg/kg s.m.] (status nawozowy)"
    )

    @model_validator(mode="after")
    def _bmp_nadpisuje_y(self):
        # P3: wynik testu BMP traktujemy jako pomiarowy Y_CH4, jeśli nie podano wprost
        if self.BMP is not None and self.Y_CH4 is None:
            object.__setattr__(self, "Y_CH4", self.BMP)
        return self


class KonfiguracjaProcesu(BaseModel):
    tryb: TrybProcesu = TrybProcesu.mezofilny
    HRT_dni: float | None = Field(default=None, gt=0)
    OLR_kgVS_m3_d: float | None = Field(default=None, gt=0)
    eta_VS: float | None = Field(default=None, gt=0, le=1)


class KonfiguracjaWyjscia(BaseModel):
    sciezka: SciezkaWyjscia = SciezkaWyjscia.chp
    # opcjonalne nadpisania sprawności (P2)
    eta_el: float | None = Field(default=None, gt=0, le=1)
    eta_th: float | None = Field(default=None, gt=0, le=1)
    e_wlasne_frac: float | None = Field(default=None, ge=0, le=1)
    q_wlasne_frac: float | None = Field(default=None, ge=0, le=1)
    s_CH4_poslizg_frac: float | None = Field(default=None, ge=0, le=1)


class KonfiguracjaEkonomiczna(BaseModel):
    gate_fee_per_typ: dict[str, float] | None = None
    ceny: dict[str, float] | None = None
    CAPEX_zl: float | None = Field(default=None, ge=0)
    OPEX_zl_rok: float | None = Field(default=None, ge=0)
    stopa_dysk: float | None = Field(default=None, ge=0, le=1)
    okres_lat: int | None = Field(default=None, gt=0)
    dofinansowanie_frac: float | None = Field(default=None, ge=0, le=1)


class KonfiguracjaPofermentu(BaseModel):
    areal_dostepny_ha: float | None = Field(
        default=None, ge=0, description="P3: dostępny areał rolny do zagospodarowania pofermentu"
    )


class WejscieSymulacji(BaseModel):
    poziom: Poziom = Poziom.podstawowy
    wsad: list[WsadSubstrat] = Field(min_length=1)
    proces: KonfiguracjaProcesu = Field(default_factory=KonfiguracjaProcesu)
    wyjscie: KonfiguracjaWyjscia = Field(default_factory=KonfiguracjaWyjscia)
    ekonomia: KonfiguracjaEkonomiczna = Field(default_factory=KonfiguracjaEkonomiczna)
    poferment: KonfiguracjaPofermentu = Field(default_factory=KonfiguracjaPofermentu)


# --------------------------------------------------------------------------- #
# Wyjście
# --------------------------------------------------------------------------- #


class WynikEnergia(BaseModel):
    biogaz_Nm3: float
    CH4_Nm3: float
    E_CH4_kWh: float
    E_el_brutto_kWh: float | None = None
    E_el_netto_kWh: float | None = None
    Q_th_brutto_kWh: float | None = None
    Q_th_netto_kWh: float | None = None
    biometan_Nm3: float | None = None
    E_biometan_kWh: float | None = None


class WynikPoferment(BaseModel):
    masa_Mg: float
    frakcja_stala_Mg: float
    frakcja_ciekla_Mg: float
    NPK_kg_rok: dict[str, float]
    status_nawozowy: str
    chlonnosc_ha_wymagana: float
    wariant_zagospodarowania: dict[str, float]
    wariant_glowny: str


class WynikEkonomia(BaseModel):
    przychody_roczne: float
    koszty_roczne: float
    CF_rok: float
    NPV: float
    IRR: float | None
    LCOE: float | None
    LCOH: float | None
    payback_lat: float | None
    rozbicie_przychodow: dict[str, float]
    wrazliwosc: dict[str, dict[str, float]] = Field(default_factory=dict)


class WynikBilansMasy(BaseModel):
    wsad_Mg: float
    biogaz_Mg: float
    poferment_Mg: float
    domkniecie_proc: float
    spojnosc_gaz_so_proc: float


class WynikSymulacji(BaseModel):
    poziom: Poziom
    energia: WynikEnergia
    poferment: WynikPoferment
    ekonomia: WynikEkonomia
    bilans_masy: WynikBilansMasy
    posrednie: dict[str, float] = Field(
        default_factory=dict, description="Wartości pośrednie (wyjaśnialność wyniku)"
    )
    ostrzezenia: list[str] = Field(default_factory=list)
