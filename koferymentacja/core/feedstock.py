"""Charakterystyka i mieszanka wsadu (substraty).

Rozwiązuje (resolve) charakterystykę każdego substratu: wartości zmierzone
(poziom 2/3) nadpisują wartości tablicowe z katalogu (poziom 1). Liczy ładunek
suchej masy organicznej (s.m.o. / VS) oraz parametry mieszanki.

Funkcje są czyste: przyjmują dane wejściowe i katalog, zwracają wynik i listę
ostrzeżeń. Stan i wczytywanie plików należą do warstwy orkiestracji.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CharakterystykaSubstratu:
    """Rozwiązana charakterystyka pojedynczego substratu (po nadpisaniach)."""

    typ: str
    masa_roczna_Mg: float
    TS_frac: float
    VS_frac: float
    Y_CH4: float
    f_CH4: float
    NPK_kg_per_Mg: dict[str, float]
    vs_load_Mg: float  # ładunek s.m.o. [Mg VS/rok]
    # czy dany parametr pochodzi z pomiaru (True) czy z tablicy (False)
    zrodlo_pomiarowe: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Mieszanka:
    """Zagregowana mieszanka wsadu."""

    substraty: list[CharakterystykaSubstratu]
    masa_calkowita_Mg: float
    vs_load_calkowity_Mg: float
    f_CH4_sredni: float  # ważony objętością metanu udział CH4 w biogazie
    proporcje_masowe: dict[str, float]


def vs_load(masa_roczna_Mg: float, ts_frac: float, vs_frac: float) -> float:
    """Ładunek s.m.o. (4.1): VS_load = masa * TS * VS  [Mg VS/rok]."""
    return masa_roczna_Mg * ts_frac * vs_frac


def _wybierz(zmierzona, domyslna):
    """Zwraca wartość zmierzoną, jeśli podana, inaczej tablicową."""
    return domyslna if zmierzona is None else zmierzona


def resolve_substrat(wejscie, katalog: dict) -> tuple[CharakterystykaSubstratu, list[str]]:
    """Łączy wejście użytkownika z domyślnymi wartościami tablicowymi.

    ``wejscie`` to obiekt z atrybutami: typ, masa_roczna_Mg oraz opcjonalnie
    TS_frac, VS_frac, Y_CH4, f_CH4 (None = brak pomiaru, użyj tablicy).
    ``katalog`` to słownik ``substraty.json["substraty"]``.
    """
    ostrzezenia: list[str] = []
    typ = wejscie.typ
    if typ not in katalog:
        raise KeyError(f"Nieznany typ substratu: {typ!r}")
    dom = katalog[typ]

    ts = _wybierz(getattr(wejscie, "TS_frac", None), dom["TS_frac"])
    vs = _wybierz(getattr(wejscie, "VS_frac", None), dom["VS_frac"])
    y = _wybierz(getattr(wejscie, "Y_CH4", None), dom["Y_CH4"])
    f = _wybierz(getattr(wejscie, "f_CH4", None), dom["f_CH4"])

    zrodlo = {
        "TS_frac": getattr(wejscie, "TS_frac", None) is not None,
        "VS_frac": getattr(wejscie, "VS_frac", None) is not None,
        "Y_CH4": getattr(wejscie, "Y_CH4", None) is not None,
        "f_CH4": getattr(wejscie, "f_CH4", None) is not None,
    }

    masa = wejscie.masa_roczna_Mg
    if masa < 0:
        raise ValueError(f"Masa roczna substratu {typ!r} nie może być ujemna: {masa}")

    load = vs_load(masa, ts, vs)

    char = CharakterystykaSubstratu(
        typ=typ,
        masa_roczna_Mg=masa,
        TS_frac=ts,
        VS_frac=vs,
        Y_CH4=y,
        f_CH4=f,
        NPK_kg_per_Mg=dict(dom.get("NPK_kg_per_Mg", {"N": 0.0, "P": 0.0, "K": 0.0})),
        vs_load_Mg=load,
        zrodlo_pomiarowe=zrodlo,
    )
    return char, ostrzezenia


def zbuduj_mieszanke(wejscia: list, katalog: dict) -> tuple[Mieszanka, list[str]]:
    """Buduje mieszankę ze wszystkich substratów.

    f_CH4 mieszanki jest ważony oczekiwaną objętością metanu każdego substratu
    (VS_load * Y_CH4), bo to ona decyduje o składzie biogazu w mieszaninie.
    """
    ostrzezenia: list[str] = []
    substraty: list[CharakterystykaSubstratu] = []
    for w in wejscia:
        char, ostrz = resolve_substrat(w, katalog)
        substraty.append(char)
        ostrzezenia.extend(ostrz)

    masa_calk = sum(s.masa_roczna_Mg for s in substraty)
    vs_calk = sum(s.vs_load_Mg for s in substraty)

    # ważony udział CH4 — wagą jest spodziewana produkcja metanu
    wagi = [s.vs_load_Mg * s.Y_CH4 for s in substraty]
    suma_wag = sum(wagi)
    if suma_wag > 0:
        f_sredni = sum(w * s.f_CH4 for w, s in zip(wagi, substraty)) / suma_wag
    else:
        # brak produkcji metanu (np. same osady przefermentowane) — średnia masowa
        f_sredni = (
            sum(s.masa_roczna_Mg * s.f_CH4 for s in substraty) / masa_calk
            if masa_calk > 0
            else 0.0
        )
        ostrzezenia.append(
            "Zerowa spodziewana produkcja metanu w mieszance — sprawdź skład wsadu."
        )

    proporcje = (
        {s.typ: s.masa_roczna_Mg / masa_calk for s in substraty}
        if masa_calk > 0
        else {s.typ: 0.0 for s in substraty}
    )

    return (
        Mieszanka(
            substraty=substraty,
            masa_calkowita_Mg=masa_calk,
            vs_load_calkowity_Mg=vs_calk,
            f_CH4_sredni=f_sredni,
            proporcje_masowe=proporcje,
        ),
        ostrzezenia,
    )
