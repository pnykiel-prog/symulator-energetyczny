"""Orkiestracja: wejście -> silnik -> wynik.

Stan wyłącznie w tej warstwie; funkcje silnika pozostają bezstanowe. Tu też
żyją: walidacja literaturowa (ostrzeżenia o wartościach poza zakresem), kontrola
Buswella (P3) i analiza wrażliwości (P2+, przez ponowne przeliczenie łańcucha).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from . import config
from .config import Katalog
from .core import digestate, digestion, economics, energy
from .core.feedstock import zbuduj_mieszanke
from .io_layer import report
from .io_layer.schema import Poziom, SciezkaWyjscia, WejscieSymulacji, WynikSymulacji


@dataclass
class _Overrides:
    """Mnożniki do analizy wrażliwości (1.0 = bez zmiany)."""

    Y_CH4: float = 1.0
    gate_fee: float = 1.0
    c_el: float = 1.0
    CAPEX: float = 1.0
    stopa_dysk: float = 1.0


@dataclass
class _WynikLancucha:
    mieszanka: object
    ferment: object
    energia_chp: object
    energia_bm: object
    poferment: object
    ekonomia: object
    posrednie: dict
    ostrzezenia: list


def _waliduj_zakresy(mieszanka, proces_par, katalog: Katalog) -> list[str]:
    """Walidacja literaturowa: wartości poza zakresem z katalogu -> ostrzeżenie."""
    ostrz: list[str] = []
    for s in mieszanka.substraty:
        zakr = katalog.substraty[s.typ].get("zakres", {})
        for pole, wart in (
            ("Y_CH4", s.Y_CH4),
            ("TS_frac", s.TS_frac),
            ("VS_frac", s.VS_frac),
            ("f_CH4", s.f_CH4),
        ):
            if pole in zakr:
                lo, hi = zakr[pole]
                if not (lo <= wart <= hi):
                    ostrz.append(
                        f"[{s.typ}] {pole}={wart:g} poza zakresem literaturowym [{lo}, {hi}]."
                    )

    tryb = proces_par["tryb"]
    zakr_proc = katalog.proces["tryby"][tryb].get("zakres", {})
    for pole in ("HRT_dni", "OLR_kgVS_m3_d", "eta_VS"):
        if pole in zakr_proc:
            lo, hi = zakr_proc[pole]
            wart = proces_par[pole]
            if not (lo <= wart <= hi):
                ostrz.append(f"[proces/{tryb}] {pole}={wart:g} poza zakresem [{lo}, {hi}].")
    return ostrz


def _kontrola_buswella(wejscie: WejscieSymulacji, mieszanka, katalog: Katalog) -> list[str]:
    """P3: Y_CH4 nie powinno przekraczać teoretycznego maksimum Buswella."""
    ostrz: list[str] = []
    bus = katalog.buswell
    osiagalne = bus["osiagalne_frac_teorii"]["wartosc"]
    vm = bus["objetosc_molowa_Nm3_per_kmol"]["wartosc"]
    masy = bus["masy_molowe_kg_per_kmol"]
    wej_po_typie = {w.typ.value: w for w in wejscie.wsad}
    for s in mieszanka.substraty:
        w = wej_po_typie.get(s.typ)
        if w is None or w.sklad_pierwiastkowy is None:
            continue
        y_max = digestion.buswell_max_y_ch4(w.sklad_pierwiastkowy, masy, vm)
        if s.Y_CH4 > y_max:
            ostrz.append(
                f"[{s.typ}] Y_CH4={s.Y_CH4:g} > teoretyczne maksimum Buswella {y_max:.0f} NL/kg VS."
            )
        elif s.Y_CH4 > osiagalne * y_max:
            ostrz.append(
                f"[{s.typ}] Y_CH4={s.Y_CH4:g} przekracza praktycznie osiągalne "
                f"{osiagalne:.0%} maksimum ({osiagalne * y_max:.0f} NL/kg VS)."
            )
    return ostrz


def _uruchom_lancuch(
    wejscie: WejscieSymulacji,
    katalog: Katalog,
    ov: _Overrides,
) -> _WynikLancucha:
    """Pełny łańcuch obliczeniowy dla danego zestawu nadpisań (overrides)."""
    ostrzezenia: list[str] = []

    proces_par = config.parametry_procesu(katalog, wejscie.proces)
    ekon_par = config.parametry_ekonomiczne(katalog, wejscie.ekonomia)

    # --- wsad ---
    mieszanka, ostrz = zbuduj_mieszanke(wejscie.wsad, katalog.substraty)
    ostrzezenia.extend(ostrz)

    # --- fermentacja ---
    ferment = digestion.fermentuj(mieszanka, proces_par["eta_VS"], katalog.Wo_CH4)
    if ov.Y_CH4 != 1.0:
        ferment = dataclasses.replace(
            ferment,
            V_CH4_Nm3=ferment.V_CH4_Nm3 * ov.Y_CH4,
            V_biogaz_Nm3=ferment.V_biogaz_Nm3 * ov.Y_CH4,
            E_CH4_kWh=ferment.E_CH4_kWh * ov.Y_CH4,
        )

    # --- energia (ścieżka) ---
    sciezka = wejscie.wyjscie.sciezka
    energia_chp = energia_bm = None
    if sciezka == SciezkaWyjscia.chp:
        chp_par = config.parametry_chp(katalog, wejscie.wyjscie)
        energia_chp = energy.chp(
            ferment.E_CH4_kWh,
            chp_par["eta_el"],
            chp_par["eta_th"],
            chp_par["e_wlasne_frac"],
            chp_par["q_wlasne_frac"],
        )
        e_el_netto = energia_chp.E_el_netto_kWh
        q_th_netto = energia_chp.Q_th_netto_kWh
        e_biometan = 0.0
    else:
        bm_par = config.parametry_biometan(katalog, wejscie.wyjscie)
        energia_bm = energy.biometan(
            ferment.V_CH4_Nm3,
            ferment.V_biogaz_Nm3,
            bm_par["s_CH4_poslizg_frac"],
            katalog.Wo_CH4,
            bm_par["energia_wlasna_kWh_per_Nm3_biogazu"],
        )
        e_el_netto = q_th_netto = 0.0
        e_biometan = energia_bm.E_biometan_kWh

    # --- poferment ---
    bilans = digestate.bilans_masy(
        mieszanka.masa_calkowita_Mg,
        ferment.V_CH4_Nm3,
        ferment.V_biogaz_Nm3,
        mieszanka.vs_load_calkowity_Mg,
        proces_par["eta_VS"],
        katalog.stale["gestosc_CH4_kg_per_Nm3"]["wartosc"],
        katalog.stale["gestosc_CO2_kg_per_Nm3"]["wartosc"],
        proces_par["u_frakcja_stala"],
    )
    npk = digestate.npk_pofermentu(mieszanka)
    ts_pof = 0.05  # przybliżony udział s.m. pofermentu do oceny metali
    metale = next((w.metale_ciezkie for w in wejscie.wsad if w.metale_ciezkie), None)
    status, ostrz_status = digestate.status_nawozowy(metale, ts_pof, katalog.limity_metali)
    ostrzezenia.extend(ostrz_status)
    chlonnosc, wariant, wariant_glowny, ostrz_chl = digestate.chlonnosc_rolnicza(
        npk,
        bilans.poferment_Mg,
        katalog.limit_azotanowy,
        wejscie.poferment.areal_dostepny_ha,
        status,
    )
    ostrzezenia.extend(ostrz_chl)

    poferment_wynik = digestate.WynikPofermentu(
        bilans=bilans,
        NPK_kg_rok=npk,
        status_nawozowy=status,
        chlonnosc_ha_wymagana=chlonnosc,
        wariant_zagospodarowania=wariant,
        wariant_glowny=wariant_glowny,
    )

    # --- ekonomia ---
    gate_fee = {k: v * ov.gate_fee for k, v in ekon_par["gate_fee_per_typ"].items()}
    ceny = dict(ekon_par["ceny"])
    ceny["c_el_zl_per_kWh"] = ceny["c_el_zl_per_kWh"] * ov.c_el
    pozostalosci = wariant.get("pelet_palny", 0.0)  # masa nie zagospodarowana rolniczo
    masy_per_typ = {s.typ: s.masa_roczna_Mg for s in mieszanka.substraty}
    przychody = economics.przychody_roczne(
        masy_per_typ,
        gate_fee,
        e_el_netto,
        q_th_netto,
        e_biometan,
        bilans.poferment_Mg,
        pozostalosci,
        ceny,
    )
    ekon = economics.metryki_finansowe(
        przychody,
        ekon_par["OPEX_zl_rok"],
        ekon_par["CAPEX_zl"] * ov.CAPEX,
        ekon_par["dofinansowanie_frac"],
        ekon_par["stopa_dysk"] * ov.stopa_dysk,
        ekon_par["okres_lat"],
        e_el_netto,
        q_th_netto,
    )
    ostrzezenia.extend(ekon.ostrzezenia)

    posrednie = {
        "vs_load_calkowity_Mg": mieszanka.vs_load_calkowity_Mg,
        "f_CH4_sredni": mieszanka.f_CH4_sredni,
        "vs_destroyed_deklar_Mg": ferment.vs_destroyed_Mg,
        "E_CH4_kWh": ferment.E_CH4_kWh,
        "eta_VS_deklar": proces_par["eta_VS"],
        "eta_VS_implikowany": bilans.spojnosc_gaz_so_proc / 100.0,
        "masa_biogazu_Mg": bilans.biogaz_Mg,
        "masa_wsadu_Mg": mieszanka.masa_calkowita_Mg,
    }

    return _WynikLancucha(
        mieszanka=mieszanka,
        ferment=ferment,
        energia_chp=energia_chp,
        energia_bm=energia_bm,
        poferment=poferment_wynik,
        ekonomia=ekon,
        posrednie=posrednie,
        ostrzezenia=ostrzezenia,
    )


def _analiza_wrazliwosci(
    wejscie: WejscieSymulacji, katalog: Katalog, npv_bazowy: float
) -> dict[str, dict[str, float]]:
    """Wpływ +/- delta każdego parametru na NPV (4.6 / sekcja 5 P2)."""
    delta = katalog.ekonomia["wrazliwosc"]["delta_frac"]
    parametry = katalog.ekonomia["wrazliwosc"]["parametry"]
    mapowanie = {
        "gate_fee": "gate_fee",
        "c_el": "c_el",
        "CAPEX": "CAPEX",
        "stopa_dysk": "stopa_dysk",
        "Y_CH4": "Y_CH4",
    }
    wynik: dict[str, dict[str, float]] = {}
    for p in parametry:
        atrybut = mapowanie[p]
        ov_dol = _Overrides(**{atrybut: 1 - delta})
        ov_gora = _Overrides(**{atrybut: 1 + delta})
        npv_dol = _uruchom_lancuch(wejscie, katalog, ov_dol).ekonomia.NPV
        npv_gora = _uruchom_lancuch(wejscie, katalog, ov_gora).ekonomia.NPV
        wynik[p] = {
            "npv_dol": npv_dol,
            "npv_gora": npv_gora,
            "wplyw_npv_dol": npv_dol - npv_bazowy,
            "wplyw_npv_gora": npv_gora - npv_bazowy,
        }
    return wynik


def symuluj(wejscie: WejscieSymulacji | dict, katalog: Katalog | None = None) -> WynikSymulacji:
    """Główny punkt wejścia modułu: liczy pełen łańcuch i składa wynik."""
    if isinstance(wejscie, dict):
        wejscie = WejscieSymulacji.model_validate(wejscie)
    if katalog is None:
        katalog = Katalog.domyslny()

    lancuch = _uruchom_lancuch(wejscie, katalog, _Overrides())
    ostrzezenia = list(lancuch.ostrzezenia)

    # walidacja literaturowa + Buswell
    proces_par = config.parametry_procesu(katalog, wejscie.proces)
    ostrzezenia.extend(_waliduj_zakresy(lancuch.mieszanka, proces_par, katalog))
    if wejscie.poziom == Poziom.precyzyjny:
        ostrzezenia.extend(_kontrola_buswella(wejscie, lancuch.mieszanka, katalog))

    # bilans masy — implikowany rozkład s.m.o. nie może przekroczyć 100% (niefizyczny)
    spojnosc = lancuch.poferment.bilans.spojnosc_gaz_so_proc
    if spojnosc > 100.0:
        ostrzezenia.append(
            f"Implikowany rozkład s.m.o. = {spojnosc:.0f}% (masa biogazu przekracza "
            "ładunek organiczny) — Y_CH4 zbyt wysokie względem wsadu, sprawdź dane."
        )

    # wrażliwość tylko od poziomu profesjonalnego
    wrazliwosc: dict = {}
    if wejscie.poziom in (Poziom.profesjonalny, Poziom.precyzyjny):
        wrazliwosc = _analiza_wrazliwosci(wejscie, katalog, lancuch.ekonomia.NPV)

    return report.zbuduj_wynik(
        poziom=wejscie.poziom,
        mieszanka=lancuch.mieszanka,
        ferment=lancuch.ferment,
        energia_chp=lancuch.energia_chp,
        energia_bm=lancuch.energia_bm,
        poferment=lancuch.poferment,
        ekonomia=lancuch.ekonomia,
        wrazliwosc=wrazliwosc,
        posrednie=lancuch.posrednie,
        ostrzezenia=ostrzezenia,
    )
