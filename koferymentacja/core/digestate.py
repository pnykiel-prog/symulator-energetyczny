"""Poferment: bilans masy, NPK, status nawozowy i chłonność rolnicza.

Implementuje równania 4.5 (bilans masy) oraz model chłonności rolniczej z
poziomu 3 (limit azotanowy 170 kg N/ha -> automatyczna hierarchia
zagospodarowania: nawóz -> pelet nawozowy -> pelet palny).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import units


@dataclass(frozen=True)
class BilansMasy:
    wsad_Mg: float
    biogaz_Mg: float
    poferment_Mg: float
    frakcja_stala_Mg: float
    frakcja_ciekla_Mg: float
    domkniecie_proc: float          # (biogaz + poferment) / wsad * 100
    spojnosc_gaz_so_proc: float     # implikowany rozkład s.m.o.: m_biogaz / VS_load * 100
    VS_destroyed_deklar_Mg: float   # VS_load * η_VS (deklarowany rozkład, diagnostyka)


@dataclass(frozen=True)
class WynikPofermentu:
    bilans: BilansMasy
    NPK_kg_rok: dict[str, float]
    status_nawozowy: str
    chlonnosc_ha_wymagana: float
    wariant_zagospodarowania: dict[str, float]  # rozbicie masy POF na ścieżki [Mg]
    wariant_glowny: str
    ostrzezenia: list[str] = field(default_factory=list)


def masa_biogazu(
    v_ch4_Nm3: float,
    v_biogaz_Nm3: float,
    gestosc_CH4: float,
    gestosc_CO2: float,
) -> float:
    """Masa biogazu [Mg/rok] z rzeczywistego składu (CH4 + CO2).

    Wierniejsze niż stała gęstość uśredniona, bo udział CH4 zmienia gęstość
    mieszaniny. Pozostałe składniki (H2S, NH3, para) pomijalne masowo.
    """
    v_co2 = max(v_biogaz_Nm3 - v_ch4_Nm3, 0.0)
    masa_kg = v_ch4_Nm3 * gestosc_CH4 + v_co2 * gestosc_CO2
    return units.kg_to_mg(masa_kg)


def bilans_masy(
    masa_wsadu_Mg: float,
    v_ch4_Nm3: float,
    v_biogaz_Nm3: float,
    vs_load_calkowity_Mg: float,
    eta_vs: float,
    gestosc_CH4: float,
    gestosc_CO2: float,
    u_frakcja_stala: float,
) -> BilansMasy:
    """Bilans masy (4.5).

    Masa biogazu wynika z rzeczywiście wyprodukowanego gazu (z Y_CH4) — to ona
    fizycznie opuszcza komorę i wiąże bilans z wynikiem energetycznym.
    m_POF = wsad - m_biogaz, więc domknięcie jest z definicji 100%.

    ``spojnosc_gaz_so_proc`` = implikowany rozkład s.m.o. (m_biogaz / VS_load):
    udział ładunku organicznego, który opuścił układ jako gaz. Wartość > 100%
    jest niefizyczna i powinna wywołać ostrzeżenie w warstwie orkiestracji.
    ``VS_destroyed_deklar`` (VS_load * η_VS) raportujemy jako diagnostykę.
    """
    m_biogaz = masa_biogazu(v_ch4_Nm3, v_biogaz_Nm3, gestosc_CH4, gestosc_CO2)
    m_biogaz = min(m_biogaz, masa_wsadu_Mg)  # gaz nie może przekroczyć wsadu
    m_pof = masa_wsadu_Mg - m_biogaz
    m_frakcja_stala = m_pof * u_frakcja_stala
    m_frakcja_ciekla = m_pof - m_frakcja_stala

    domkniecie = (
        (m_biogaz + m_pof) / masa_wsadu_Mg * 100.0 if masa_wsadu_Mg > 0 else 100.0
    )
    spojnosc = (
        m_biogaz / vs_load_calkowity_Mg * 100.0 if vs_load_calkowity_Mg > 0 else 0.0
    )

    return BilansMasy(
        wsad_Mg=masa_wsadu_Mg,
        biogaz_Mg=m_biogaz,
        poferment_Mg=m_pof,
        frakcja_stala_Mg=m_frakcja_stala,
        frakcja_ciekla_Mg=m_frakcja_ciekla,
        domkniecie_proc=domkniecie,
        spojnosc_gaz_so_proc=spojnosc,
        VS_destroyed_deklar_Mg=vs_load_calkowity_Mg * eta_vs,
    )


def npk_pofermentu(mieszanka) -> dict[str, float]:
    """Ładunek NPK w pofermencie [kg/rok].

    Azot, fosfor i potas praktycznie pozostają w pofermencie (nie ulatniają się
    z biogazem), więc ładunek = Σ masa_i * zawartość_i.
    """
    suma = {"N": 0.0, "P": 0.0, "K": 0.0}
    for s in mieszanka.substraty:
        for k in suma:
            suma[k] += s.masa_roczna_Mg * s.NPK_kg_per_Mg.get(k, 0.0)
    return suma


def status_nawozowy(
    metale_ciezkie: dict | None,
    ts_pofermentu_frac: float,
    limity_mg_per_kg_sm: dict,
) -> tuple[str, list[str]]:
    """Ocena dopuszczalności nawozowej na podstawie metali ciężkich (P3).

    ``metale_ciezkie`` w mg/kg s.m. pofermentu. Brak danych -> status
    nieokreślony (poziom 1/2).
    """
    ostrzezenia: list[str] = []
    if not metale_ciezkie:
        return "nieokreslony_brak_danych", ostrzezenia

    przekroczenia = []
    for metal, wartosc in metale_ciezkie.items():
        limit = limity_mg_per_kg_sm.get(metal)
        if limit is None:
            continue
        if wartosc > limit:
            przekroczenia.append(f"{metal}={wartosc} > limit {limit} mg/kg s.m.")

    if przekroczenia:
        ostrzezenia.append(
            "Przekroczenie limitów metali ciężkich dla nawozu: "
            + "; ".join(przekroczenia)
        )
        return "nienawozowy_przekroczone_metale", ostrzezenia
    return "nawozowy", ostrzezenia


def chlonnosc_rolnicza(
    npk_kg_rok: dict[str, float],
    poferment_Mg: float,
    limit_azotanowy_kgN_per_ha: float,
    areal_dostepny_ha: float | None,
    status: str,
) -> tuple[float, dict[str, float], str, list[str]]:
    """Model chłonności rolniczej i hierarchii zagospodarowania (P3).

    Wymagany areał = N_total / limit_azotanowy. Jeśli dostępny areał jest
    mniejszy, nadwyżka masy pofermentu trafia do peletu nawozowego (gdy status
    nawozowy OK) lub peletu palnego (gdy nie).
    """
    ostrzezenia: list[str] = []
    n_total = npk_kg_rok.get("N", 0.0)
    chlonnosc_wymagana = (
        n_total / limit_azotanowy_kgN_per_ha if limit_azotanowy_kgN_per_ha > 0 else 0.0
    )

    wariant = {"nawoz": 0.0, "pelet_nawozowy": 0.0, "pelet_palny": 0.0}

    if poferment_Mg <= 0:
        return chlonnosc_wymagana, wariant, "brak", ostrzezenia

    # tylko jawne przekroczenie metali dyskwalifikuje; brak danych -> traktuj
    # warunkowo jako nawozowy (ocena metali to funkcja poziomu 3)
    nawozowy_ok = status != "nienawozowy_przekroczone_metale"
    sciezka_nadwyzki = "pelet_nawozowy" if nawozowy_ok else "pelet_palny"

    if areal_dostepny_ha is None:
        # poziom < 3: brak modelu chłonności, cały poferment jako nawóz/pelet
        if nawozowy_ok:
            wariant["nawoz"] = poferment_Mg
            return chlonnosc_wymagana, wariant, "nawoz", ostrzezenia
        wariant["pelet_palny"] = poferment_Mg
        ostrzezenia.append(
            "Status nienawozowy — poferment skierowany do peletu palnego."
        )
        return chlonnosc_wymagana, wariant, "pelet_palny", ostrzezenia

    if not nawozowy_ok:
        wariant["pelet_palny"] = poferment_Mg
        ostrzezenia.append(
            "Status nienawozowy — całość pofermentu do peletu palnego mimo dostępnego areału."
        )
        return chlonnosc_wymagana, wariant, "pelet_palny", ostrzezenia

    if areal_dostepny_ha >= chlonnosc_wymagana:
        wariant["nawoz"] = poferment_Mg
        wariant_glowny = "nawoz"
    else:
        # część masy mieści się w limicie azotanowym, reszta jako pelet
        frac_na_pole = (
            areal_dostepny_ha / chlonnosc_wymagana if chlonnosc_wymagana > 0 else 1.0
        )
        masa_na_pole = poferment_Mg * frac_na_pole
        wariant["nawoz"] = masa_na_pole
        wariant[sciezka_nadwyzki] = poferment_Mg - masa_na_pole
        wariant_glowny = "nawoz+" + sciezka_nadwyzki
        ostrzezenia.append(
            f"Dostępny areał {areal_dostepny_ha:.1f} ha < wymagany {chlonnosc_wymagana:.1f} ha "
            f"(limit azotanowy {limit_azotanowy_kgN_per_ha} kg N/ha). "
            f"Nadwyżka {wariant[sciezka_nadwyzki]:.0f} Mg -> {sciezka_nadwyzki}."
        )

    return chlonnosc_wymagana, wariant, wariant_glowny, ostrzezenia
