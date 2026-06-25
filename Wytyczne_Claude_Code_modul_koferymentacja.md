# Wytyczne implementacyjne dla Claude Code — moduł koferymentacyjny

**Co budujemy:** moduł symulatora „Odpady → Energia" oparty na koferymentacji osadów ściekowych i bioodpadów. Moduł liczy łańcuch *wsad → biogaz → energia/ciepło (lub biometan) → poferment → wynik ekonomiczny* i zwraca efekt energetyczny oraz finansowy instalacji.

**Kontekst:** to jeden z modułów cyfrowego bliźniaka gmin (obok modułów: budynek, sieć, technologie, ekonomia). Moduł jest **lokalnym, sterowalnym źródłem** zasilającym bilans społeczności energetycznej. Architektura ma być **modułowa**, stack **Python**, a warstwą danych jest gotowy **katalog parametrów** (`Katalog_parametrow_koferymentacja.xlsx`).

---

## 1. Zasady nadrzędne (przeczytaj przed pisaniem kodu)

1. **Silnik = czyste funkcje.** Logika obliczeniowa jako funkcje bez efektów ubocznych, w pełni testowalne. Żadnych wartości wpisanych na sztywno w kod.
2. **Współczynniki pochodzą z konfiguracji, nie z kodu.** Wszystkie `Y_CH4`, `f_CH4`, sprawności, ceny itd. ładowane z plików danych (JSON/YAML) wygenerowanych z katalogu parametrów. Zmiana współczynnika = zmiana danych, nie kodu.
3. **Jeden model danych dla wszystkich poziomów.** Wzorzec z modułu budynku: zaczynamy od poziomu 1, a wyższe poziomy *dokładają* parametry i wierność, nie przebudowują struktur. Poziom to atrybut konfiguracji wejścia, nie osobny program.
4. **Spójność jednostek wymuszona w jednym miejscu.** Łańcuch Mg/rok → Nm³ → kWh/MWh → zł. Konwersje w jednym module, nie rozproszone.
5. **Każdy wynik ma być wyjaśnialny.** Moduł raportuje nie tylko liczby końcowe, ale i pośrednie (ładunek s.m.o., objętość metanu, potrzeby własne), żeby dało się prześledzić skąd wynik.
6. **Walidacja względem zakresów z katalogu.** Wynik poza zakresem literaturowym → ostrzeżenie, nie cichy błąd.

---

## 2. Struktura projektu (propozycja)

```
koferymentacja/
├── data/
│   ├── substraty.json          # Y_CH4, f_CH4, TS, VS — z arkusza "Współczynniki uzysku"
│   ├── proces.json             # domyślne HRT, OLR, T, η_VS
│   ├── chp.json                # η_el, η_th, potrzeby własne
│   ├── ekonomia.json           # ceny, stawki, stopa dysk. (puste do uzupełnienia lokalnie)
│   └── stale.json              # Wo_CH4, limit azotanowy itd.
├── core/
│   ├── units.py                # konwersje jednostek (jedyne miejsce)
│   ├── feedstock.py            # charakterystyka i mieszanka wsadu
│   ├── digestion.py            # silnik fermentacji: wsad → biogaz → metan
│   ├── energy.py               # CHP / biometan, potrzeby własne, eksport netto
│   ├── digestate.py            # poferment: frakcje, NPK, chłonność rolnicza
│   └── economics.py            # przychody, koszty, NPV/IRR/LCOE/LCOH, wrażliwość
├── io/
│   ├── schema.py               # walidowane modele wejścia/wyjścia (pydantic)
│   └── report.py               # generowanie wyniku (energ. + finans. + bilans masy)
├── config.py                   # ładowanie data/*, wybór poziomu
├── simulate.py                 # orkiestracja: wejście → silnik → wynik
└── tests/                      # testy jednostkowe + walidacja literaturowa
```

**Stack:** Python 3.11+, `pydantic` (walidacja schematów), `numpy` (obliczenia), `numpy-financial` (NPV/IRR), `pytest` (testy). Bez ciężkich zależności — to moduł obliczeniowy, nie aplikacja.

---

## 3. Model danych

**Wejście** (walidowane, pola opcjonalne wg poziomu):

```
WsadSubstrat:
  typ: enum                    # osady_wstepne | osady_nadmierne | osady_mieszane |
                               # osady_przefermentowane | bio_kuchenne | bio_zielone | bio_mieszane
  masa_roczna_Mg: float        # P1
  TS_frac: float | None        # P2 (udział s.m.)
  VS_frac: float | None        # P2 (udział s.m.o. w s.m.)
  Y_CH4: float | None          # P2/P3 (NL CH4/kg s.m.o.) — nadpisuje tablicę
  f_CH4: float | None          # P2
  BMP: float | None            # P3 (z testu)
  sklad_pierwiastkowy: dict|None  # P3 (C,H,O,N,S) — kontrola Buswella
  metale_ciezkie: dict | None  # P3 — status nawozowy

KonfiguracjaProcesu:
  proporcja: dict              # {osady: 0.7, bio: 0.3} — P2
  tryb: enum                   # mezofilny | termofilny — P1
  HRT_dni, OLR, eta_VS: ...    # P2

KonfiguracjaWyjscia:
  sciezka: enum                # chp | biometan
  ...sprawności wg chp.json / bm.json

KonfiguracjaEkonomiczna:
  gate_fee, ceny, CAPEX, OPEX, stopa_dysk, okres, dofinansowanie

poziom: enum                   # podstawowy | profesjonalny | precyzyjny
```

**Wyjście:**

```
WynikSymulacji:
  energia: { biogaz_Nm3, CH4_Nm3, E_el_brutto, E_el_netto,
             Q_th_brutto, Q_th_netto, biometan_Nm3 }   # zależnie od ścieżki
  poferment: { masa_Mg, frakcja_stala_Mg, NPK, status_nawozowy,
               chlonnosc_ha_wymagana, wariant_zagospodarowania }
  ekonomia: { przychody_roczne, koszty_roczne, NPV, IRR, LCOE, LCOH,
              payback_lat, wrażliwość }
  bilans_masy: { wsad_Mg, biogaz_Mg, poferment_Mg, domknięcie_% }
  ostrzeżenia: [ ... ]         # wartości poza zakresem, brak danych itp.
```

---

## 4. Silnik obliczeniowy (równania)

Implementuj dokładnie ten łańcuch. Jednostki dobrane tak, że tysiące się skracają — pilnuj tego w `units.py`.

```
# 4.1 Ładunek suchej masy organicznej (per substrat)
VS_load_i [Mg VS/rok] = masa_i · TS_i · VS_i

# 4.2 Metan (per substrat) — uwaga jednostkowa:
# Y_CH4 w NL CH4/kg VS, VS_load w Mg VS → wynik w Nm³ (mnożniki 1000 się skracają)
V_CH4_i [Nm³/rok] = VS_load_i · Y_CH4_i
V_CH4 = Σ V_CH4_i
V_biogaz = V_CH4 / f_CH4_śr           # objętość biogazu (do bilansu/uszlachetniania)

# 4.3 Energia w metanie
E_CH4 [kWh/rok] = V_CH4 · Wo_CH4       # Wo_CH4 = 9,97 kWh/Nm³ (stała)

# 4.4a Ścieżka CHP
E_el_brutto = E_CH4 · η_el
Q_th_brutto = E_CH4 · η_th
E_el_netto  = E_el_brutto · (1 − e_wł)
Q_th_netto  = Q_th_brutto · (1 − q_wł)

# 4.4b Ścieżka biometan
V_biometan = V_CH4 · (1 − s_CH4)       # poślizg metanu
E_biometan = V_biometan · Wo_CH4

# 4.5 Poferment (bilans masy)
VS_destroyed = Σ VS_load_i · η_VS
m_biogaz     ≈ przelicz(VS_destroyed)  # masa odprowadzona jako gaz
m_POF        = Σ masa_i − m_biogaz
m_frakcja_stała = m_POF · u_stała

# 4.6 Ekonomia
R_rok = Σ(gate_fee_i · masa_i) + E_el_netto·c_el + Q_th_netto·c_th
        + E_biometan·c_bm + m_POF·c_POF + pozostałości·c_skł_unikn
C_rok = OPEX
CF_rok = R_rok − C_rok
CAPEX_netto = CAPEX · (1 − dofinansowanie)
NPV  = Σ_t [ CF_t / (1+r)^t ] − CAPEX_netto
IRR  = r : NPV = 0
LCOE = (annualizowany CAPEX + OPEX) / E_el_netto
LCOH = analogicznie dla ciepła
payback = CAPEX_netto / CF_rok          # prosty
```

**Kontrola teoretyczna (P3):** z `sklad_pierwiastkowy` policz maksymalny `Y_CH4` równaniem Buswella; osiągalne ≈ 92% maksimum (wg VDI 4630). Jeśli `Y_CH4` z danych > teoria → ostrzeżenie.

---

## 5. Podział na poziomy — inkrementalny plan budowy

Buduj **w tej kolejności**. Każdy poziom to działający, przetestowany produkt; kolejny dokłada wierność na tym samym modelu danych.

### Poziom 1 — Podstawowy (MVP silnika)
**Wejście:** masy strumieni + typ substratu. Reszta z `data/*.json` (wartości domyślne tablicowe).
**Liczy:** ładunek s.m.o. (z domyślnych TS/VS per typ) → biogaz → metan → energia (CHP, sprawności domyślne) → uproszczona ekonomia (przychody roczne, prosty payback).
**Pomija:** parametry procesu, potrzeby własne (lub stały ryczałt), analizę wrażliwości, NPK pofermentu (tylko masa).
**Cel:** szybki szacunek „czy to ma sens", roczny bilans statyczny.

### Poziom 2 — Profesjonalny
**Dokłada:** zmierzone właściwości wsadu (TS, VS), parametry procesu (HRT, OLR, T, η_VS), realne sprawności CHP i potrzeby własne, ścieżkę biometanu jako wariant, **pełną ekonomię** (NPV, IRR, LCOE, LCOH) i **analizę wrażliwości** (gate fee, ceny energii, CAPEX, stopa dysk., Y_CH4), bilans pofermentu z NPK i podziałem na frakcje.
**Cel:** wynik wiarygodny dla decyzji inwestycyjnej.

### Poziom 3 — Precyzyjny
**Dokłada:** `Y_CH4` z testu **BMP** zamiast tablicy, kontrolę teoretyczną Buswella ze składu pierwiastkowego, **model chłonności rolniczej pofermentu** (dostępny areał + limit azotanowy 170 kg N/ha·rok → automatyczne przełączenie hierarchii zagospodarowania: nawóz → pelet nawozowy → pelet palny), opcjonalnie **kinetykę** (Gompertz/ADM1) z profilem czasowym produkcji, oraz **tryb kalibracji** względem danych eksploatacyjnych instalacji.
**Cel:** najwyższa wierność, podstawa kalibracji i raportu końcowego.

> Zasada wspólna: nie buduj trzech osobnych silników. Buduj jeden, w którym brak danych wyższego poziomu jest wypełniany wartością domyślną niższego, a poziom steruje tym, które ścieżki się uruchamiają.

---

## 6. Walidacja i testy (obowiązkowe)

- **Testy jednostkowe** każdej funkcji silnika z ręcznie policzonymi przypadkami.
- **Walidacja literaturowa:** dla typowego wsadu wynik `Y_CH4` i uzysk energii mają mieścić się w zakresach z arkusza „Współczynniki uzysku". Test sprawdza zakres, nie punktową równość.
- **Kontrola Buswella:** test, że `Y_CH4` nie przekracza teoretycznego maksimum.
- **Domknięcie bilansu masy:** wsad = biogaz + poferment + pozostałości; tolerancja błędu < kilka %.
- **Przypadki brzegowe:** zerowy strumień, sam jeden substrat, przefermentowane osady (uzysk bliski zeru).
- **Zero błędów liczbowych:** brak dzielenia przez zero (np. LCOE przy zerowej produkcji — obsłuż jawnie).

---

## 7. Sprzężenie z resztą symulatora

Moduł zwraca **interfejs wyjściowy** zgodny z resztą cyfrowego bliźniaka:
- energia elektryczna i ciepło (netto) → bilans społeczności / moduł sieci (źródło sterowalne, stabilizujące zmienne PV/wiatr);
- biometan → wyjście alternatywne (sieć gazowa);
- wskaźniki ekonomiczne (NPV/IRR/LCOE/LCOH) → wspólny moduł ekonomiczny;
- nie implementuj tu optymalizacji sieci ani bilansowania społeczności — moduł ma *dostarczać* wynik, nie domykać całego systemu.

---

## 8. Plan pracy (kamienie milowe dla Claude Code)

| Etap | Zakres | Kryterium ukończenia |
|---|---|---|
| M1 | `units`, `feedstock`, `digestion`, `energy` (ścieżka CHP) + dane P1 + testy | Poziom 1 liczy biogaz→energię z testami przechodzącymi |
| M2 | `economics` (NPV/IRR/LCOE/LCOH + wrażliwość), `digestate` (NPK), ścieżka biometanu | Poziom 2 daje pełny wynik finansowy + bilans pofermentu |
| M3 | Buswell, kinetyka, model chłonności pofermentu, tryb kalibracji | Poziom 3 + kalibracja na danych testowych |
| M4 | `io/report`, interfejs wyjściowy do modułu społeczności | Wynik w formacie zgodnym z resztą bliźniaka |

---

## 9. Konwencje

- Kod i nazwy w kodzie po angielsku; komentarze i terminy domenowe po polsku tam, gdzie to zwiększa czytelność (`Y_CH4`, `poferment`).
- Typowanie statyczne (type hints) wszędzie; modele wejścia/wyjścia przez `pydantic`.
- Żadnych magicznych liczb — stałe (Wo_CH4, limit azotanowy) w `data/stale.json`.
- Funkcje silnika bezstanowe; stan tylko w warstwie orkiestracji.
- Każda wartość domyślna w `data/*.json` opatrzona polem `źródło` (jak w katalogu).

> Ten dokument jest specyfikacją modułu. Może też posłużyć jako baza pliku `CLAUDE.md` w repozytorium — wtedy sekcje 1, 2 i 9 (zasady, struktura, konwencje) warto przenieść na górę jako stałe wytyczne dla agenta.
