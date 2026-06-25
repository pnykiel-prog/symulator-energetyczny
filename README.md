# Moduł koferymentacyjny — symulator „Odpady → Energia"

Moduł cyfrowego bliźniaka gmin liczący efekt energetyczny i finansowy
instalacji **koferymentacji** osadów ściekowych i bioodpadów. Realizuje łańcuch:

```
wsad → biogaz → energia/ciepło (CHP) lub biometan → poferment → wynik ekonomiczny
```

Stanowi **lokalne, sterowalne źródło** w bilansie społeczności energetycznej
(stabilizuje zmienne PV/wiatr). Moduł *dostarcza* wynik — nie domyka bilansu
całej społeczności ani nie optymalizuje sieci.

## Instalacja

```bash
pip install -e .                 # instalacja pakietu (zalecane)
# albo
pip install -r requirements.txt
```

Wymaga Python ≥ 3.11. Zależności: `pydantic`, `numpy`, `numpy-financial`
(+ `pytest` do testów).

## Szybki start

```python
from koferymentacja import symuluj

wynik = symuluj({
    "poziom": "profesjonalny",
    "wsad": [
        {"typ": "osady_mieszane", "masa_roczna_Mg": 12000},
        {"typ": "bio_kuchenne",   "masa_roczna_Mg": 6000, "Y_CH4": 470},
    ],
    "wyjscie": {"sciezka": "chp"},
    "ekonomia": {"CAPEX_zl": 22_000_000, "dofinansowanie_frac": 0.4},
})

print(wynik.energia.E_el_netto_kWh)   # energia elektryczna netto [kWh/rok]
print(wynik.ekonomia.NPV)             # NPV [zł]
print(wynik.poferment.wariant_glowny) # sposób zagospodarowania pofermentu
for o in wynik.ostrzezenia:
    print("⚠", o)
```

Pełne demo trzech poziomów: `python examples/przyklad.py`.

## Interfejs web (samodzielna aplikacja)

Moduł jest **samodzielny** — gmina może uruchomić tylko tę część symulatora,
z własnym interfejsem, w oderwaniu od reszty cyfrowego bliźniaka. Ta sama
aplikacja FastAPI (silnik + cienka warstwa we/wy) działa w trzech trybach bez
zmian w kodzie:

**Lokalnie (u gminy):**
```bash
pip install -e ".[web]"
uvicorn koferymentacja.web.app:app --reload
# formularz: http://127.0.0.1:8000/   ·   dokumentacja API: http://127.0.0.1:8000/docs
```

**Docker (własny serwer):**
```bash
docker build -t koferymentacja .
docker run -p 8000:8000 koferymentacja
```

**Vercel (chmura, serverless):** repozytorium zawiera `vercel.json` i
`api/index.py`. Po podłączeniu repo do Vercela deploy jest automatyczny —
funkcja serverless serwuje formularz i API. Obliczenia trwają ułamki sekundy,
więc limity czasu wykonania nie są problemem.

### Endpointy

| Metoda | Ścieżka | Opis |
|---|---|---|
| `GET` | `/` | Formularz web (HTML) |
| `POST` | `/api/symuluj` | Uruchamia symulację (JSON wejściowy → `WynikSymulacji`) |
| `GET` | `/api/meta` | Metadane do zbudowania formularza (typy, poziomy, domyślne) |
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Interaktywna dokumentacja API (Swagger) |

```bash
curl -X POST http://127.0.0.1:8000/api/symuluj -H "Content-Type: application/json" \
  -d '{"poziom":"profesjonalny","wsad":[{"typ":"osady_mieszane","masa_roczna_Mg":12000}]}'
```

## Poziomy wierności

Jeden silnik, jeden model danych — poziom steruje tym, które dane są używane
i które ścieżki się uruchamiają. Brak danych wyższego poziomu jest uzupełniany
wartością domyślną z katalogu (`data/*.json`).

| Poziom | Co dokłada |
|---|---|
| **podstawowy** | masy + typy strumieni; reszta z tablic; CHP; uproszczona ekonomia (payback) |
| **profesjonalny** | zmierzone TS/VS, parametry procesu, realne sprawności, ścieżka biometanu, pełna ekonomia (NPV/IRR/LCOE/LCOH) + analiza wrażliwości, NPK pofermentu |
| **precyzyjny** | `Y_CH4` z testu BMP, kontrola teoretyczna Buswella, model chłonności rolniczej (limit azotanowy 170 kg N/ha → hierarchia: nawóz → pelet nawozowy → pelet palny) |

## Wejście (skrót)

- `wsad`: lista substratów — `typ` (osady_wstepne / osady_nadmierne /
  osady_mieszane / osady_przefermentowane / bio_kuchenne / bio_zielone /
  bio_mieszane), `masa_roczna_Mg`, opcjonalnie `TS_frac`, `VS_frac`, `Y_CH4`,
  `f_CH4`, `BMP`, `sklad_pierwiastkowy`, `metale_ciezkie`.
- `proces`: `tryb` (mezofilny / termofilny), `HRT_dni`, `OLR_kgVS_m3_d`, `eta_VS`.
- `wyjscie`: `sciezka` (chp / biometan) + opcjonalne sprawności.
- `ekonomia`: `gate_fee_per_typ`, `ceny`, `CAPEX_zl`, `OPEX_zl_rok`,
  `stopa_dysk`, `okres_lat`, `dofinansowanie_frac`.
- `poferment`: `areal_dostepny_ha` (model chłonności, P3).

Wejście jest walidowane przez `pydantic`. Pełny schemat:
`koferymentacja/io_layer/schema.py`.

## Wyjście

`WynikSymulacji` (pydantic) zawiera: `energia`, `poferment`, `ekonomia`,
`bilans_masy`, `posrednie` (wartości pośrednie — wyjaśnialność) oraz
`ostrzezenia`. Eksport do dict/JSON: `wynik.model_dump()`.

## Warstwa danych

Cała wiedza liczbowa jest w `koferymentacja/data/*.json`, każda wartość
opatrzona polem `źródło`. Zmiana współczynnika = edycja danych, nie kodu.
Wartości reprezentują literaturę (ATV-DVWK, Weiland 2010, VDI 4630 i in.) —
do nadpisania danymi lokalnej instalacji.

## Testy

```bash
python -m pytest
```

Obejmują: testy jednostkowe silnika (ręcznie policzone przypadki), walidację
literaturową zakresów, kontrolę Buswella, domknięcie bilansu masy, przypadki
brzegowe (zerowy strumień, osady przefermentowane) i jawną obsługę dzielenia
przez zero (LCOE przy zerowej produkcji).

## Sprzężenie z resztą symulatora

- energia el. i ciepło (netto) → bilans społeczności / moduł sieci,
- biometan → wyjście alternatywne (sieć gazowa),
- NPV/IRR/LCOE/LCOH → wspólny moduł ekonomiczny.
