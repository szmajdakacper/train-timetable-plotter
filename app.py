import streamlit as st
import datetime as dt
import hashlib

from excel_loader import read_and_store_in_session
from table_editor import save_cell_time, clear_cell_time, propagate_time_shift
from utils import parse_time, format_time_hhmm
from train_grid_component.backend.train_grid_component import train_grid
from train_plot_component.backend.train_plot_component import train_plot


st.set_page_config(layout="wide", page_title="wykresy z tabeli - KD")

st.title("Rozkład Jazdy - wykresy z tabeli")

uploaded_file = st.file_uploader("Prześlij plik Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # zapamiętaj nazwę wczytanego pliku do nazwania eksportu
        try:
            st.session_state["uploaded_name"] = str(uploaded_file.name)
        except Exception:
            pass
        file_bytes = uploaded_file.getvalue()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if st.session_state.get("uploaded_hash") != file_hash:
            read_and_store_in_session(file_bytes, st.session_state)
            st.session_state["uploaded_hash"] = file_hash
            st.success("Dane wczytane i zapisane do st.session_state")
    except Exception as e:
        st.error(f"Nie udało się wczytać pliku: {e}")

"""Tabela km – stacja – pociągi"""
station_map = st.session_state.get("station_map", {})
sheets_data = st.session_state.get("sheets_data", [])

if station_map and sheets_data:
    # Selektor arkusza w obramowaniu z aktywnym stylem (radio poziome)
    sheet_names = [entry.get("sheet") for entry in sheets_data]
    if "selected_sheet" not in st.session_state:
        st.session_state.selected_sheet = sheet_names[0] if sheet_names else None

    with st.container(border=True):
        st.markdown("**Arkusz:**")
        selected_sheet = st.radio(
            label="Arkusz",
            label_visibility="collapsed",
            options=sheet_names,
            horizontal=True,
            index=(sheet_names.index(st.session_state.selected_sheet)
                   if st.session_state.selected_sheet in sheet_names else 0),
            key="sheet_radio",
        )
    st.session_state.selected_sheet = selected_sheet

    # Filtr danych do wybranego arkusza
    active = next((entry for entry in sheets_data if entry.get("sheet") == selected_sheet), {"trains": []})
    trains_active = active.get("trains", [])

    # Przyciski akcji
    with st.container(border=True):
        col_dl, _ = st.columns([1,5])

        def _hhmm_from_any(val: any) -> str:
            try:
                if isinstance(val, (int, float)):
                    d = float(val)
                else:
                    d = parse_time(val)
                if d is None:
                    return ""
                return format_time_hhmm(d)
            except Exception:
                return ""

        def build_excel_bytes() -> bytes:
            from io import BytesIO
            from openpyxl import Workbook
            from utils import normalize

            wb = Workbook()
            # usuń domyślny arkusz
            try:
                wb.remove(wb.active)
            except Exception:
                pass

            station_maps_all = st.session_state.get("station_maps", {})

            for entry in sheets_data:
                sheet_name = str(entry.get("sheet"))
                ws = wb.create_sheet(title=sheet_name[:31] or "Arkusz")

                # Nagłówki stałe
                ws["E3"] = "numer pociągu"
                ws["D11"] = "km"
                ws["E11"] = "ze stacji"

                # Lista stacji/km z mapy wybranego arkusza (dla każdego arkusza jego własna mapa)
                station_map_sheet = station_maps_all.get(sheet_name, {})
                stations_sorted = sorted(station_map_sheet.items(), key=lambda kv: kv[1])

                start_row = 12
                for idx, (station_name, km_val) in enumerate(stations_sorted):
                    r = start_row + idx
                    # km jako liczba (Excel wyświetli przecinek wg regionalnych ustawień), 3 miejsca po przecinku
                    c_km = ws.cell(row=r, column=4, value=float(km_val))  # D
                    try:
                        c_km.number_format = "0.000"
                    except Exception:
                        pass
                    ws.cell(row=r, column=5, value=str(station_name))       # E

                # "do stacji" w wierszu po ostatniej stacji
                ws.cell(row=start_row + len(stations_sorted), column=5, value="do stacji")

                # Kolumny pociągów – unikalne numery
                trains_list = entry.get("trains", [])
                train_nums = sorted({ str(t.get("train_number")) for t in trains_list })
                # wiersz 3 od kolumny F w prawo
                for j, tn in enumerate(train_nums):
                    ws.cell(row=3, column=6 + j, value=tn)

                # Zbuduj mapę czasów: (station, tn) -> time oraz (normalize(station), tn) -> time
                # Preferuj time_decimal do formatowania
                key_to_time = {}
                key_to_time_norm = {}
                for rec in trains_list:
                    st_name = rec.get("station")
                    tn = str(rec.get("train_number"))
                    t_fmt = _hhmm_from_any(rec.get("time_decimal") if rec.get("time_decimal") is not None else rec.get("time"))
                    key_to_time[(st_name, tn)] = t_fmt
                    key_to_time_norm[(normalize(str(st_name)), tn)] = t_fmt

                # Wypełnij czasy wg stacji i numerów pociągów
                for i, (station_name, km_val) in enumerate(stations_sorted):
                    r = start_row + i
                    for j, tn in enumerate(train_nums):
                        t_str = key_to_time.get((station_name, tn), "") or key_to_time_norm.get((normalize(str(station_name)), tn), "")
                        if t_str:
                            ws.cell(row=r, column=6 + j, value=t_str)

            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            return buf.getvalue()

        with col_dl:
            xbytes = build_excel_bytes()
            export_name = st.session_state.get("uploaded_name") or "rozkład.xlsx"
            st.download_button(
                label="Pobierz rozkład do xlsx",
                data=xbytes,
                file_name=export_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # Zbuduj kolumny pociągów (tylko z wybranego arkusza)
    train_numbers = [str(t["train_number"]) for t in trains_active]
    unique_trains = sorted(set(train_numbers), key=lambda x: (''.join(ch for ch in x if ch.isdigit()) == "", x))

    # Wiersze bazujemy na mapie stacji z wybranego arkusza, posortowane po km rosnąco
    station_maps = st.session_state.get("station_maps", {})
    active_station_map = station_maps.get(selected_sheet, station_map)
    station_items = sorted(active_station_map.items(), key=lambda kv: kv[1])

    # Zbuduj strukturę: {(station, km): {train_number: time_display}} tylko dla wybranego arkusza
    cell_map = {}
    for rec in trains_active:
        key = (rec["station"], float(rec["km"]))
        bucket = cell_map.setdefault(key, {})
        # Preferuj time_decimal, aby ujednolicić wyświetlanie bez sufiksu (+d)
        try:
            tdec = float(rec.get("time_decimal")) if rec.get("time_decimal") is not None else None
        except Exception:
            tdec = None
        if tdec is None:
            parsed = parse_time(rec.get("time"))
            tdec = float(parsed) if parsed is not None else None
        if tdec is not None:
            display_val = format_time_hhmm(tdec)
        else:
            display_val = str(rec.get("time") or "")
        bucket[str(rec["train_number"]) ] = display_val

    # Render: tabela
    import pandas as pd
    table_rows = []
    for station, km in ((name, km) for name, km in station_items):
        row = {"km": f"{km:.3f}", "stacja": station}
        times = cell_map.get((station, float(km)), {})
        for tn in unique_trains:
            row[tn] = times.get(tn, "")
        table_rows.append(row)

    df_view = pd.DataFrame(table_rows)

    # Wykres tras (nad tabelą)
    st.subheader("Wykres tras pociągów")
    plot_height = st.slider("Wysokość wykresu", min_value=600, max_value=4000, value=600, step=100, key="plot_height")
    # Oś Y: km (zaznaczamy stacje z mapy aktywnego arkusza jako markery)
    y_stations = [{"name": name, "km": float(km)} for name, km in station_items]

    # Budowa serii: dla każdego pociągu z KAŻDEGO arkusza punkty [czas_ms, indeks_stacji]
    def hours_to_ms(hours_float: float) -> int:
        return int(float(hours_float) * 3600000.0)

    # Zbuduj dla każdego arkusza mapę: station -> {train_number: time}
    sheet_to_station_train = {}
    sheet_to_trains = {}
    for entry in sheets_data:
        sheet = entry.get("sheet")
        station_to_train = {}
        trains = entry.get("trains", [])
        for rec in trains:
            station_name = rec["station"]
            tn = str(rec["train_number"]) 
            station_bucket = station_to_train.setdefault(station_name, {})
            station_bucket[tn] = rec["time"]
        sheet_to_station_train[sheet] = station_to_train
        sheet_to_trains[sheet] = sorted({ str(t["train_number"]) for t in trains })

    # Dla osi Y wykorzystujemy km z wybranego arkusza; rysujemy WSZYSTKIE pociągi z KAŻDEGO arkusza
    station_to_km_selected = { name: float(km) for name, km in station_items }

    series = []
    global_min_ms = None
    global_max_ms = None
    for sheet, station_to_train in sheet_to_station_train.items():
        for tn in sheet_to_trains.get(sheet, []):
            pts = []
            base_time = None
            for station_name, km_selected in station_items:
                time_str = station_to_train.get(station_name, {}).get(tn, "")
                if not time_str:
                    continue
                parsed = parse_time(time_str)
                if parsed is None:
                    continue
                # korekta przekroczenia północy – gdy różnica > 12h, dodaj 24h
                if base_time is None:
                    adj = parsed
                    base_time = parsed
                else:
                    if parsed < base_time and (base_time - parsed) > 12:
                        adj = parsed + 24
                    else:
                        adj = parsed
                    if parsed > base_time and (parsed - base_time) > 12:
                        base_time = parsed
                ms = hours_to_ms(adj)
                pts.append({
                    "value": [ms, float(km_selected)],
                    "station": station_name,
                    "train": tn,
                    "sheet": sheet,
                })
                global_min_ms = ms if global_min_ms is None else min(global_min_ms, ms)
                global_max_ms = ms if global_max_ms is None else max(global_max_ms, ms)
            if pts:
                # Nazwa serii zawiera arkusz, by rozróżnić te same numery pociągów w różnych arkuszach
                series.append({"name": f"{tn} ({sheet})", "points": pts})

    # Dynamiczny zakres X z marginesem: lewy -2h dla etykiet, prawy +30 min
    pad_left = 2 * 60 * 60 * 1000
    pad_right = 30 * 60 * 1000
    x_min = max(0, (global_min_ms or 0) - pad_left)
    x_max = (global_max_ms or (24 * 3600 * 1000)) + pad_right

    # Nonce do resetu komponentu wykresu po akcji w modalu
    plot_nonce_key = f"plot_nonce_{selected_sheet}"
    if plot_nonce_key not in st.session_state:
        st.session_state[plot_nonce_key] = 0

    evt_plot = train_plot(
        y_stations=y_stations,
        series=series,
        x_min_ms=x_min,
        x_max_ms=x_max,
        key=f"plot_{selected_sheet}_{st.session_state[plot_nonce_key]}",
        height=int(plot_height or 600),
    )


    # Obsługa dblclick z wykresu (edycja czasu w dowolnym arkuszu)
    if evt_plot and isinstance(evt_plot, dict) and evt_plot.get("type") == "pointDoubleClick":
        try:
            col_id = str(evt_plot.get("train") or "")
            station_clicked = str(evt_plot.get("station") or "")
            km_clicked = float(evt_plot.get("km") or 0.0)
            # arkusz może być None — wtedy użyj aktualnego
            sheet_clicked = str(evt_plot.get("sheet") or selected_sheet)
        except Exception:
            col_id, station_clicked, km_clicked, sheet_clicked = "", "", 0.0, selected_sheet

        # km dla propagacji i zapisu bierzemy z mapy stacji właściwego arkusza
        try:
            km_sheet_clicked = float(st.session_state.get("station_maps", {}).get(sheet_clicked, {}).get(station_clicked, km_clicked))
        except Exception:
            km_sheet_clicked = km_clicked

        # Domyślna godzina z eventu (ms od północy, z obsługą doby >24h)
        try:
            ms_val = float(evt_plot.get("ms"))
            parsed = ms_val / 3600000.0
        except Exception:
            parsed = None
        default_time = dt.time(int(parsed) % 24, int(round((parsed % 1) * 60))) if parsed is not None else dt.time(0, 0)

        try:
            @st.experimental_dialog("Edycja czasu (z wykresu)")
            def time_dialog_plot():
                st.write(f"Arkusz: {sheet_clicked}  •  Stacja: {station_clicked}  •  km: {km_sheet_clicked:.3f}  •  Pociąg: {col_id}")
                t = st.time_input("Godzina", value=default_time, step=dt.timedelta(minutes=1), key=f"dlg_time_plot_{sheet_clicked}")
                allow_propagate = parsed is not None
                prop = st.checkbox("Uwzględnij zmianę na dalszej części trasy", value=True, disabled=not allow_propagate, key=f"dlg_prop_plot_{sheet_clicked}")
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    if st.button("Zapisz", type="primary", key=f"dlg_save_plot_{sheet_clicked}"):
                        if prop and parsed is not None:
                            new_dec = float(t.hour) + float(t.minute)/60.0 + float(getattr(t, 'second', 0))/3600.0
                            delta_hours = new_dec - float(parsed)
                        else:
                            delta_hours = 0.0
                        save_cell_time(sheet_clicked, station_clicked, float(km_sheet_clicked), col_id, t, st.session_state)
                        if prop and delta_hours != 0.0:
                            propagate_time_shift(sheet_clicked, col_id, float(km_sheet_clicked), float(delta_hours), st.session_state)
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()
                with c2:
                    if st.button("Usuń postój", key=f"dlg_clear_plot_{sheet_clicked}"):
                        clear_cell_time(sheet_clicked, station_clicked, float(km_sheet_clicked), col_id, st.session_state)
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()
                with c3:
                    if st.button("Anuluj", key=f"dlg_cancel_plot_{sheet_clicked}"):
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()

            time_dialog_plot()
        except Exception as e:
            # Fallback: panel zamiast modala
            st.warning(f"Nie udało się otworzyć okna dialogowego wykresu: {e}")
            with st.container(border=True):
                st.write(f"Arkusz: {sheet_clicked}  •  Stacja: {station_clicked}  •  km: {km_sheet_clicked:.3f}  •  Pociąg: {col_id}")
                t = st.time_input("Godzina", value=default_time, step=dt.timedelta(minutes=1), key=f"fallback_time_plot_{sheet_clicked}")
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    if st.button("Zapisz", type="primary", key=f"fallback_save_plot_{sheet_clicked}"):
                        save_cell_time(sheet_clicked, station_clicked, float(km_sheet_clicked), col_id, t, st.session_state)
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()
                with c2:
                    if st.button("Usuń postój", key=f"fallback_clear_plot_{sheet_clicked}"):
                        clear_cell_time(sheet_clicked, station_clicked, float(km_sheet_clicked), col_id, st.session_state)
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()
                with c3:
                    if st.button("Anuluj", key=f"fallback_cancel_plot_{sheet_clicked}"):
                        st.session_state[plot_nonce_key] += 1
                        st.rerun()

    st.subheader("Tabela: km – stacja – pociągi")
    st.caption(f"Arkusz: {selected_sheet}")

    # Nonce do wymuszenia resetu siatki po akcji w modalu
    grid_nonce_key = f"grid_nonce_{selected_sheet}"
    if grid_nonce_key not in st.session_state:
        st.session_state[grid_nonce_key] = 0
    # Zbuduj columnDefs i wywołaj custom component
    import pandas as pd
    train_cols = [c for c in df_view.columns if c not in ("km", "stacja")]
    column_defs = (
        [
            {"field": "km", "headerName": "km", "editable": False, "width": 60},
            {"field": "stacja", "headerName": "stacja", "editable": False, "width": 60},
        ]
        + [{"field": c, "headerName": c, "editable": True, "width": 120} for c in train_cols]
    )

    row_data = df_view.to_dict(orient="records")
    grid_height = min(600, 100 + 26 * (len(df_view) + 1))

    evt = train_grid(
        row_data=row_data,
        column_defs=column_defs,
        key=f"grid_{selected_sheet}_{st.session_state[grid_nonce_key]}",
        height=grid_height,
        theme="ag-theme-alpine",
    )

    # Obsługa eventów z komponentu
    if evt and isinstance(evt, dict) and evt.get("type") == "cellDoubleClick":
        col_id = str(evt.get("field") or "")
        if col_id and col_id not in ("km", "stacja"):
            row = evt.get("row") or {}
            station_clicked = str(row.get("stacja") or "")
            try:
                km_clicked = float(str(row.get("km") or "0").replace(",", "."))
            except Exception:
                km_clicked = 0.0

            # Ustal domyślną godzinę z danych
            current_time_str = cell_map.get((station_clicked, float(km_clicked)), {}).get(col_id, "")
            parsed = parse_time(current_time_str) if current_time_str else None
            default_time = dt.time(int(parsed) % 24, int(round((parsed % 1) * 60))) if parsed is not None else dt.time(0, 0)

            # Modal dialog edycji czasu (wymaga Streamlit 1.34+)
            try:
                @st.experimental_dialog("Edycja czasu")
                def time_dialog():
                    st.write(f"Stacja: {station_clicked}  •  km: {km_clicked:.3f}  •  Pociąg: {col_id}")
                    t = st.time_input("Godzina", value=default_time, step=dt.timedelta(minutes=1), key=f"dlg_time_{selected_sheet}")
                    # Checkbox propagacji tylko jeśli istniała poprzednia wartość czasu (mamy parsed)
                    allow_propagate = parsed is not None
                    prop = st.checkbox("Uwzględnij zmianę na dalszej części trasy", value=True, disabled=not allow_propagate, key=f"dlg_prop_{selected_sheet}")
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1:
                        if st.button("Zapisz", type="primary", key=f"dlg_save_{selected_sheet}"):
                            # Oblicz delta względem poprzedniej wartości jeśli propagacja aktywna
                            if prop and parsed is not None:
                                new_dec = float(t.hour) + float(t.minute)/60.0 + float(getattr(t, 'second', 0))/3600.0
                                delta_hours = new_dec - float(parsed)
                            else:
                                delta_hours = 0.0

                            save_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, t, st.session_state)
                            if prop and delta_hours != 0.0:
                                propagate_time_shift(selected_sheet, col_id, float(km_clicked), float(delta_hours), st.session_state)
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()
                    with c2:
                        if st.button("Usuń postój", key=f"dlg_clear_{selected_sheet}"):
                            clear_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, st.session_state)
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()
                    with c3:
                        if st.button("Anuluj", key=f"dlg_cancel_{selected_sheet}"):
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()

                time_dialog()
            except Exception as e:
                # Fallback: panel zamiast modala
                st.warning(f"Nie udało się otworzyć okna dialogowego: {e}")
                with st.container(border=True):
                    st.write(f"Stacja: {station_clicked}  •  km: {km_clicked:.3f}  •  Pociąg: {col_id}")
                    t = st.time_input("Godzina", value=default_time, step=dt.timedelta(minutes=1), key=f"fallback_time_{selected_sheet}")
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1:
                        if st.button("Zapisz", type="primary", key=f"fallback_save_{selected_sheet}"):
                            save_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, t, st.session_state)
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()
                    with c2:
                        if st.button("Usuń postój", key=f"fallback_clear_{selected_sheet}"):
                            clear_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, st.session_state)
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()
                    with c3:
                        if st.button("Anuluj", key=f"fallback_cancel_{selected_sheet}"):
                            st.session_state[grid_nonce_key] += 1
                            st.rerun()
else:
    st.info("Brak danych do zbudowania tabeli. Wczytaj plik.")

st.markdown("---")

# Debugowy podgląd danych zapisanych w stanie aplikacji

st.title("🧪 Debug: Excel → session state")

st.subheader("Mapa stacji (z 1. arkusza)")
if station_map:
    st.json(station_map)
else:
    st.info("Brak danych. Wczytaj plik.")

st.subheader("Weryfikacja spójności listy stacji we wszystkich arkuszach")
station_check = st.session_state.get("station_check", {"ok": False, "mismatches": []})
st.write("Zgodność:", "TAK" if station_check.get("ok") else "NIE")
if station_check.get("mismatches"):
    st.json(station_check["mismatches"])

st.subheader("Dane pociągów per arkusz")
if sheets_data:
    for entry in sheets_data:
        st.markdown(f"**Arkusz:** {entry.get('sheet')}")
        trains = entry.get("trains", [])
        if not trains:
            st.write("(brak danych pociągów)")
            continue
        minimal_view = [
            {
                "train_number": t["train_number"],
                "station": t["station"],
                "km": t["km"],
                "time": t["time"],
            }
            for t in trains
        ]
        st.dataframe(minimal_view, use_container_width=True)
else:
    st.info("Brak danych pociągów. Wczytaj plik.")

# Footer – profesjonalny podpis
footer_year = dt.date.today().year
st.markdown(
    f"""
    <style>
    .app-footer {{ position: fixed; left: 0; right: 0; bottom: 0; padding: 6px 10px; text-align: center; color: #666; background: rgba(0,0,0,0.03); font-size: 12px; z-index: 10000; }}
    </style>
    <div class=\"app-footer\">© {footer_year} Kacper Szmajda</div>
    """,
    unsafe_allow_html=True,
)

