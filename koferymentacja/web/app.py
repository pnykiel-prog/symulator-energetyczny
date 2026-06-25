"""Samodzielny interfejs modułu koferymentacyjnego.

Jedna aplikacja FastAPI serwująca równocześnie:
- formularz web (GET ``/``) — gmina może użyć modułu w oderwaniu od reszty
  cyfrowego bliźniaka,
- JSON API (POST ``/api/symuluj``) — do integracji programistycznej,
- metadane do zbudowania formularza (GET ``/api/meta``).

Apka jest przenośna: ten sam kod działa lokalnie (uvicorn), w Dockerze i na
Vercel (jako funkcja serverless). Silnik (``symuluj``) pozostaje nietknięty —
to tylko cienka warstwa we/wy.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ..config import Katalog
from ..io_layer.schema import (
    Poziom,
    SciezkaWyjscia,
    TrybProcesu,
    TypSubstratu,
    WejscieSymulacji,
    WynikSymulacji,
)
from ..simulate import symuluj

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Moduł koferymentacyjny — symulator „Odpady → Energia”",
    description=(
        "Samodzielny moduł cyfrowego bliźniaka gmin: wsad → biogaz → "
        "energia/ciepło (lub biometan) → poferment → wynik ekonomiczny."
    ),
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def strona_glowna() -> str:
    """Serwuje formularz web."""
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    """Metadane do zbudowania formularza: typy substratów, poziomy, ścieżki,
    domyślne wartości ekonomiczne (do wstępnego wypełnienia pól)."""
    katalog = Katalog.domyslny()
    inwest = katalog.ekonomia["inwestycja"]
    substraty = {
        typ: {
            "TS_frac": dane["TS_frac"],
            "VS_frac": dane["VS_frac"],
            "Y_CH4": dane["Y_CH4"],
            "opis": dane.get("źródło", ""),
        }
        for typ, dane in katalog.substraty.items()
    }
    return {
        "poziomy": [p.value for p in Poziom],
        "typy_substratow": [t.value for t in TypSubstratu],
        "tryby": [t.value for t in TrybProcesu],
        "sciezki": [s.value for s in SciezkaWyjscia],
        "substraty": substraty,
        "ekonomia_domyslna": {
            "CAPEX_zl": inwest["CAPEX_zl"],
            "OPEX_zl_rok": inwest["OPEX_zl_rok"],
            "stopa_dysk": inwest["stopa_dysk"],
            "okres_lat": inwest["okres_lat"],
            "dofinansowanie_frac": inwest["dofinansowanie_frac"],
        },
    }


@app.post("/api/symuluj", response_model=WynikSymulacji)
def api_symuluj(wejscie: WejscieSymulacji) -> WynikSymulacji:
    """Uruchamia pełen łańcuch obliczeniowy i zwraca wynik symulacji.

    Walidacja wejścia (pydantic) zwraca 422 z opisem błędu. Błędy domenowe
    (np. niespójne dane) zwracają 400.
    """
    try:
        return symuluj(wejscie)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
