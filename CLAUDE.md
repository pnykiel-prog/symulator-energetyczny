# CLAUDE.md — moduł koferymentacyjny

Stałe wytyczne dla agenta pracującego nad tym modułem. Pełna specyfikacja:
`Wytyczne_Claude_Code_modul_koferymentacja.md` (źródło wymagań).

## Czym jest moduł

Moduł symulatora „Odpady → Energia" oparty na koferymentacji osadów ściekowych
i bioodpadów. Liczy łańcuch *wsad → biogaz → energia/ciepło (lub biometan) →
poferment → wynik ekonomiczny*. To **lokalne, sterowalne źródło** dla bilansu
społeczności energetycznej cyfrowego bliźniaka gmin.

## Zasady nadrzędne (przeczytaj przed pisaniem kodu)

1. **Silnik = czyste funkcje.** Logika w `core/` bez efektów ubocznych, w pełni
   testowalna. Stan wyłącznie w warstwie orkiestracji (`simulate.py`).
2. **Współczynniki z konfiguracji, nie z kodu.** Wszystkie `Y_CH4`, `f_CH4`,
   sprawności, ceny, stałe ładowane z `data/*.json`. Zmiana współczynnika =
   zmiana danych, nie kodu. Żadnych magicznych liczb w silniku.
3. **Jeden model danych dla wszystkich poziomów.** Poziom (`podstawowy /
   profesjonalny / precyzyjny`) to atrybut wejścia. Wyższy poziom *dokłada*
   parametry; brak danych wyższego poziomu wypełniany jest domyślną niższego.
4. **Spójność jednostek w jednym miejscu** — `core/units.py`. Łańcuch
   Mg/rok → Nm³ → kWh/MWh → zł.
5. **Każdy wynik wyjaśnialny.** Raportujemy też wartości pośrednie
   (`WynikSymulacji.posrednie`): ładunek s.m.o., objętość metanu, potrzeby
   własne, implikowany rozkład s.m.o.
6. **Walidacja względem zakresów z katalogu.** Wynik poza zakresem
   literaturowym → ostrzeżenie (`ostrzezenia`), nie cichy błąd.

## Struktura

```
koferymentacja/
├── data/            # JSON: substraty, proces, chp, ekonomia, stałe (z polem "źródło")
├── core/            # silnik (czyste funkcje): units, feedstock, digestion,
│                    #   energy, digestate, economics
├── io_layer/        # schema.py (pydantic wej/wyj) + report.py
├── web/             # samodzielny interfejs: FastAPI (app.py) + static/index.html
├── config.py        # ładowanie data/*, rozwiązywanie parametrów wg poziomu
└── simulate.py      # orkiestracja: wejście → silnik → wynik + walidacja + wrażliwość
api/index.py         # punkt wejścia dla Vercel (funkcja serverless ASGI)
vercel.json          # konfiguracja deployu na Vercel (+ includeFiles dla data/static)
Dockerfile           # obraz do self-hostingu u gminy
tests/               # testy jednostkowe + walidacja literaturowa + Buswell + API
examples/przyklad.py # demo trzech poziomów
```

**Samodzielność:** moduł ma własny interfejs (`web/`), bo gmina może chcieć
tylko tę część symulatora. Ta sama apka FastAPI działa lokalnie (uvicorn),
w Dockerze i na Vercel — bez zmian w kodzie. Warstwa web jest *cienka*: opakowuje
`symuluj()`, nie dubluje logiki silnika.

> **Uwaga nazewnicza:** katalog `io/` z wytycznych nazwano `io_layer/`, aby nie
> przesłaniać modułu standardowej biblioteki `io`. Poza nazwą — zgodnie ze spec.

## Konwencje

- Kod i nazwy po angielsku; terminy domenowe po polsku tam, gdzie zwiększa
  czytelność (`Y_CH4`, `poferment`, `s.m.o.`).
- Type hints wszędzie; modele wej/wyj przez `pydantic`.
- Żadnych magicznych liczb — stałe (Wo_CH4, limit azotanowy, gęstości, limity
  metali) w `data/stale.json`.
- Funkcje silnika bezstanowe; stan tylko w orkiestracji.
- Każda wartość domyślna w `data/*.json` opatrzona polem `źródło`.

## Decyzje modelowe warte zapamiętania

- **Bilans masy** kotwiczony jest na *rzeczywiście wyprodukowanym biogazie*
  (z `Y_CH4`, gęstości CH₄/CO₂), bo to on fizycznie opuszcza komorę i wiąże
  bilans z wynikiem energetycznym. `η_VS` raportujemy jako diagnostykę
  (deklarowany vs implikowany rozkład s.m.o.). Ostrzeżenie tylko, gdy
  implikowany rozkład > 100% (niefizyczne).
- **Status nawozowy** dyskwalifikuje tylko jawne przekroczenie metali ciężkich;
  brak danych (P1/P2) → status nieokreślony, traktowany warunkowo jako nawozowy.

## Stan realizacji

Zrealizowane M1–M4: poziomy 1–3 (CHP + biometan), pełna ekonomia
(NPV/IRR/LCOE/LCOH + wrażliwość), bilans pofermentu z NPK i chłonnością
rolniczą, kontrola Buswella. Brak (świadomie, poza zakresem MVP): kinetyka
Gompertz/ADM1 z profilem czasowym oraz tryb kalibracji na danych
eksploatacyjnych (rozszerzenia P3).

## Uruchamianie

```bash
pip install -e ".[web,dev]"              # silnik + interfejs web + testy
python -m pytest                         # testy (54)
python examples/przyklad.py              # demo trzech poziomów (headless)
uvicorn koferymentacja.web.app:app --reload   # interfejs web -> http://127.0.0.1:8000/
```
