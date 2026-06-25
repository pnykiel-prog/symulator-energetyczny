"""Moduł koferymentacyjny symulatora "Odpady -> Energia".

Liczy łańcuch: wsad -> biogaz -> energia/ciepło (lub biometan) -> poferment ->
wynik ekonomiczny. Lokalne, sterowalne źródło dla bilansu społeczności
energetycznej cyfrowego bliźniaka gmin.

Publiczne API:
    >>> from koferymentacja import symuluj, WejscieSymulacji
    >>> wynik = symuluj({"wsad": [{"typ": "osady_mieszane", "masa_roczna_Mg": 10000}]})
"""

from __future__ import annotations

from .config import Katalog
from .io_layer.schema import (
    KonfiguracjaEkonomiczna,
    KonfiguracjaPofermentu,
    KonfiguracjaProcesu,
    KonfiguracjaWyjscia,
    Poziom,
    SciezkaWyjscia,
    TrybProcesu,
    TypSubstratu,
    WejscieSymulacji,
    WsadSubstrat,
    WynikSymulacji,
)
from .simulate import symuluj

__all__ = [
    "symuluj",
    "Katalog",
    "WejscieSymulacji",
    "WynikSymulacji",
    "WsadSubstrat",
    "KonfiguracjaProcesu",
    "KonfiguracjaWyjscia",
    "KonfiguracjaEkonomiczna",
    "KonfiguracjaPofermentu",
    "Poziom",
    "TypSubstratu",
    "TrybProcesu",
    "SciezkaWyjscia",
]

__version__ = "0.1.0"
