# Code Review - Train Timetable Plotter

**Data:** 2026-02-10
**Galeaz:** `code-review`
**Reviewer:** Claude Opus 4.6

---

## Podsumowanie

Projekt jest dobrze zorganizowany, z czytelnym podzialem na moduly (app, utils, table_editor, excel_loader) i dwa komponenty Streamlit (grid + plot). Kod spelnia swoje zadanie, ale ma kilka istotnych problemow do naprawienia. Ponizej lista znalezisk, posortowana wg priorytetu.

---

## BLOCKING - Bledy do naprawienia

### B1. `any` zamiast `Any` w type hintach

**Pliki:** `table_editor.py`, `excel_loader.py`
**Wystapienia:** 15+

```python
# ZLE - any to wbudowana funkcja, nie typ
sheets_data: List[Dict[str, any]] = session_state.get("sheets_data", [])

# DOBRZE - Any z modulu typing
from typing import Any
sheets_data: List[Dict[str, Any]] = session_state.get("sheets_data", [])
```

`any` (lowercase) to wbudowana funkcja Pythona. W type hintach powinna byc uzyta `Any` z `typing`. W strict mode mypy/pyright to jest blad typu. Nie powoduje runtime crash, ale psuje walidacje typow.

**Lokalizacje w table_editor.py:** linie 45, 49, 52, 55, 139, 143, 147, 201, 205, 209, 243, 247
**Lokalizacje w excel_loader.py:** linie 91, 92, 124, 163

---

### B2. Martwy kod - nieuzywane funkcje

#### `apply_table_edits()` w `table_editor.py:25-117`
Funkcja zdefiniowana, ale nigdzie nie importowana ani uzywana. 93 linie martwego kodu.

#### `extract_train_paths()` w `utils.py:364-399`
Funkcja zdefiniowana, ale nigdzie nie importowana. 36 linii martwego kodu. Jej funkcjonalnosc jest juz pokryta przez `extract_excel_data()` w `excel_loader.py`.

---

### B3. XSS w tooltip wykresu (trainPlot.tsx)

**Plik:** `train_plot_component/frontend/src/trainPlot.tsx`

Tooltip ECharts zwraca niesanityzowane dane uzytkownika w HTML:
```typescript
return `nr poc: ${train}<br/>stacja: ${station}<br/>...`;
```
Jesli nazwy stacji lub pociagow zawieraja `<script>` lub inne tagi HTML, zostana wykonane w kontekscie iframe'a. Ryzyko ograniczone (dane pochodza z Excela uploadowanego przez tego samego uzytkownika), ale jest to zla praktyka.

**Zalecenie:** Dodac escape'owanie HTML lub uzyc `textStyle` zamiast `formatter` z HTML.

---

## IMPORTANT - Istotne usprawnienia

### I1. `build_excel_bytes()` wykonywane przy kazdym renderze

**Plik:** `app.py:338`

```python
with col_dl:
    xbytes = build_excel_bytes()  # Wywolywane na KAZDYM renderze Streamlit!
```

Streamlit przebudowuje cala strone przy kazdej interakcji. `build_excel_bytes()` tworzy pelny workbook Excel za kazdym razem, nawet gdy uzytkownik nie klika "Pobierz". To operacja I/O-intensywna.

**Zalecenie:** Uzyc `st.cache_data` lub przebudowac z `@st.fragment`:
```python
@st.cache_data
def build_excel_bytes(_sheets_data, _station_maps_all):
    ...
```

---

### I2. Ogromna duplikacja kodu dialogow

**Plik:** `app.py`

Kod dialogu edycji czasu jest zduplikowany **4 razy**:
1. Dialog wykresu (linie 663-694)
2. Fallback wykresu (linie 700-730)
3. Dialog tabeli (linie 798-832)
4. Fallback tabeli (linie 838-868)

Kazdy z nich implementuje identyczna logike (save/clear/cancel + propagacja). To ~260 linii kodu, ktore moglyby byc jedna funkcja.

**Zalecenie:** Wyodrebnic logike zapisu/kasowania/propagacji do wspolnej funkcji:
```python
def _handle_time_edit(sheet, station, km, train, time_input, propagate, parsed, ...):
    ...
```

---

### I3. Inline importy w app.py

**Plik:** `app.py`

Importy wewnatrz funkcji lub srodka pliku:
- Linia 501: `import pandas as pd`
- Linia 736: `import pandas as pd` (drugi raz!)
- Linia 426: `import streamlit.components.v1 as _stc`
- Linia 224: `from io import BytesIO` (wewnatrz `build_excel_bytes`)
- Linia 225: `from openpyxl import Workbook` (wewnatrz `build_excel_bytes`)
- Linia 226: `from utils import normalize` (wewnatrz `build_excel_bytes`)

Inline importy w Streamlit czasem sie zdarzaja (lazy loading), ale podwojny import `pandas` i import `normalize` (juz dostepny z top-level scope) to bledy porprzadkowe.

---

### I4. Brak walidacji wejscia w backendach komponentow

**Pliki:** `train_grid_component/backend/train_grid_component.py`, `train_plot_component/backend/train_plot_component.py`

Funkcje `train_grid()` i `train_plot()` nie waliduja danych wejsciowych:
- `train_colors` moze zawierac nieprawidlowe kolory hex
- `series` moze miec brakujace klucze `points`
- `x_min_ms >= x_max_ms` nie jest sprawdzane

---

### I5. Niezabezpieczony dostep do `window.parent` (trainPlot.tsx)

**Plik:** `train_plot_component/frontend/src/trainPlot.tsx`

Komponent uzywa `window.parent.__trainplotZoom` do persystencji stanu zoom. Choc obsluguje bledy przez try/catch, nie waliduje struktury odczytanych danych:
```typescript
const savedZoom = (window.parent as any).__trainplotZoom;
```
Malformed dane z parent frame moga spowodowac nieprawidlowy zoom.

---

## NITS - Drobne uwagi

### N1. `_hhmm_from_any(val: any)` w app.py:211

Parametr typowany jako `any` (lowercase) - powinno byc albo bez type hinta, albo `Any`.

### N2. Nadmiarowe `except Exception: pass` w app.py

Linie 169, 232-233, 293-295, 308-309 - puste catch bloki, ktore moga ukrywac prawdziwe bledy. Np. linia 232:
```python
try:
    wb.remove(wb.active)
except Exception:
    pass
```
Lepiej zlogowaec lub przynajmniej uzyc bardziej specyficznego wyjatku.

### N3. Typy w `table_editor.py` powtarzaja `rec_key()` 3 razy

Funkcje `save_cell_time`, `clear_cell_time`, `propagate_time_shift` definiuja identyczna lokalna funkcje `rec_key()`. Powinna byc jedna funkcja na poziomie modulu.

### N4. `extract_train_columns()` w utils.py - closure w petli

**Plik:** `utils.py:313-325`

Funkcja `column_has_time(j)` jest zdefiniowana wewnatrz petli `while`, ale zamyka nad `station_rows` ktore sie nie zmienia. Mogla by byc zdefiniowana raz przed petla.

### N5. `Dict[str, float]` vs dataclass dla station_map

Station map jest uzywany wszedzie jako `Dict[str, float]`, ale nie ma formalnego typu. Wg python-best-practices lepiej byloby uzyc `NewType` lub dataclass:
```python
StationMap = NewType("StationMap", Dict[str, float])
```

### N6. Brak testow

Nie ma katalogu `tests/` ani zadnych plikow testowych. Funkcje jak `parse_time()`, `apply_midnight_correction()`, `propagate_time_shift()` sa idealnymi kandydatami do unit testow.

### N7. Magic strings

Stale jak `"p"`, `"o"`, `"cellDoubleClick"`, `"pointDoubleClick"`, `"_station_raw"`, `"_stop_type"` sa rozrzucone po calym kodzie. Lepiej wyodrebnic do stalych.

### N8. Frontend - nadmiarowe uzycie `any` w TypeScript

Oba komponenty React uzywaja `any` w wielu miejscach, co niweluje korzysci z TypeScript. Szczegolnie w `trainPlot.tsx` (27+ wystapien).

### N9. Frontend - silent catch blocks

`trainPlot.tsx` ma wiele pustych catch blockow (np. linie 91-111, 227-271), ktore ukrywaja bledy. Przynajmniej `console.warn` byloby pomocne przy debugowaniu.

### N10. Fragile series name parsing

`trainPlot.tsx` wyciaga numer pociagu z nazwy serii przez regex:
```typescript
s.name.replace(/ \([^)]+\)$/, "")
```
Jesli nazwa pociagu zawiera nawiasy (np. "IC (EIP)"), parsowanie sie psuje.

---

## CLAUDE.md - Aktualizacja

CLAUDE.md jest w wiekszosci aktualny, ale brakuje kilku informacji:

### Brakujace session state keys:
- `train_colors` - dict mapujacy numer pociagu na kolor hex
- `active_color` - aktywny kolor w trybie kolorowania (hex lub None)
- `uploaded_hash` - SHA256 hash wgranego pliku (zapobiega re-parsowaniu)
- `uploaded_name` - nazwa wgranego pliku (do exportu)
- `selected_sheet` - wybrany arkusz
- `_show_color_help` - flaga modalu instrukcji kolorow

### Brakujace typy eventow komponentow:
- Grid wysyla tez `cellClick` (tryb koloru) i `cellValueChanged` (inline edit)
- Plot wysyla tez `pointClick` (tryb koloru)

### Brakujace funkcje w opisie utils.py:
- `parse_km()` - parsowanie kilometrazu
- `apply_midnight_correction()` - korekta przejscia przez polnoc
- `format_time_hhmm()` - formatowanie HH:MM bez sufiksu dnia

### Brakujacy opis w table_editor.py:
- `apply_table_edits()` - (martwy kod, do usuniecia)

---

## Statystyki

| Metryka | Wartosc |
|---------|---------|
| Pliki Pythona | 4 (app.py, utils.py, table_editor.py, excel_loader.py) |
| Linie Pythona | ~1200 |
| Pliki TS/TSX | 4 (TrainGrid.tsx, trainPlot.tsx + 2x main.tsx) |
| Blocking issues | 3 |
| Important issues | 5 |
| Nit issues | 10 |
| Martwy kod (linie) | ~130 |

---

## Verdict

Projekt jest funkcjonalny i dobrze zorganizowany. Glowne problemy to:
1. Bledne type hinty (`any` vs `Any`) - latwy fix
2. Martwy kod do usuniecia
3. Masywna duplikacja dialogow w app.py (najwazniejszy refactor)
4. Brak testow

Zalecam naprawienie blockingowych bledow i aktualizacje CLAUDE.md. Refactor duplikacji dialogow moze byc zrobiony w osobnym PR.
