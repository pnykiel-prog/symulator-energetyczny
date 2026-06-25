"""Składanie wyniku symulacji w walidowany model wyjściowy.

Raportujemy nie tylko liczby końcowe, ale i pośrednie (ładunek s.m.o., objętość
metanu, potrzeby własne), żeby wynik był wyjaśnialny.
"""

from __future__ import annotations

from .schema import (
    Poziom,
    WynikBilansMasy,
    WynikEkonomia,
    WynikEnergia,
    WynikPoferment,
    WynikSymulacji,
)


def zbuduj_wynik(
    *,
    poziom: Poziom,
    mieszanka,
    ferment,
    energia_chp,
    energia_bm,
    poferment,
    ekonomia,
    wrazliwosc: dict,
    posrednie: dict,
    ostrzezenia: list[str],
) -> WynikSymulacji:
    """Buduje ``WynikSymulacji`` z wyników poszczególnych etapów silnika."""
    energia = WynikEnergia(
        biogaz_Nm3=ferment.V_biogaz_Nm3,
        CH4_Nm3=ferment.V_CH4_Nm3,
        E_CH4_kWh=ferment.E_CH4_kWh,
        E_el_brutto_kWh=energia_chp.E_el_brutto_kWh if energia_chp else None,
        E_el_netto_kWh=energia_chp.E_el_netto_kWh if energia_chp else None,
        Q_th_brutto_kWh=energia_chp.Q_th_brutto_kWh if energia_chp else None,
        Q_th_netto_kWh=energia_chp.Q_th_netto_kWh if energia_chp else None,
        biometan_Nm3=energia_bm.V_biometan_Nm3 if energia_bm else None,
        E_biometan_kWh=energia_bm.E_biometan_kWh if energia_bm else None,
    )

    poferment_out = WynikPoferment(
        masa_Mg=poferment.bilans.poferment_Mg,
        frakcja_stala_Mg=poferment.bilans.frakcja_stala_Mg,
        frakcja_ciekla_Mg=poferment.bilans.frakcja_ciekla_Mg,
        NPK_kg_rok=poferment.NPK_kg_rok,
        status_nawozowy=poferment.status_nawozowy,
        chlonnosc_ha_wymagana=poferment.chlonnosc_ha_wymagana,
        wariant_zagospodarowania=poferment.wariant_zagospodarowania,
        wariant_glowny=poferment.wariant_glowny,
    )

    rozbicie = ekonomia.rozbicie_przychodow
    ekonomia_out = WynikEkonomia(
        przychody_roczne=ekonomia.przychody_roczne,
        koszty_roczne=ekonomia.koszty_roczne,
        CF_rok=ekonomia.CF_rok,
        NPV=ekonomia.NPV,
        IRR=ekonomia.IRR,
        LCOE=ekonomia.LCOE,
        LCOH=ekonomia.LCOH,
        payback_lat=ekonomia.payback_lat,
        rozbicie_przychodow={
            "gate_fee": rozbicie.gate_fee,
            "energia_el": rozbicie.energia_el,
            "cieplo": rozbicie.cieplo,
            "biometan": rozbicie.biometan,
            "poferment": rozbicie.poferment,
            "skladowanie_unikniete": rozbicie.skladowanie_unikniete,
        },
        wrazliwosc=wrazliwosc,
    )

    bilans_out = WynikBilansMasy(
        wsad_Mg=poferment.bilans.wsad_Mg,
        biogaz_Mg=poferment.bilans.biogaz_Mg,
        poferment_Mg=poferment.bilans.poferment_Mg,
        domkniecie_proc=poferment.bilans.domkniecie_proc,
        spojnosc_gaz_so_proc=poferment.bilans.spojnosc_gaz_so_proc,
    )

    return WynikSymulacji(
        poziom=poziom,
        energia=energia,
        poferment=poferment_out,
        ekonomia=ekonomia_out,
        bilans_masy=bilans_out,
        posrednie=posrednie,
        ostrzezenia=ostrzezenia,
    )
