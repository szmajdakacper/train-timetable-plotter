import streamlit as st
import datetime as dt
import hashlib

from excel_loader import read_and_store_in_session
from table_editor import save_cell_time, clear_cell_time
from utils import parse_time
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode


st.set_page_config(layout="wide", page_title="Train timetable debug")

st.title("🧪 Debug: Excel → session state")

uploaded_file = st.file_uploader("Prześlij plik Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.getvalue()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        if st.session_state.get("uploaded_hash") != file_hash:
            read_and_store_in_session(file_bytes, st.session_state)
            st.session_state["uploaded_hash"] = file_hash
            st.success("Dane wczytane i zapisane do st.session_state")
    except Exception as e:
        st.error(f"Nie udało się wczytać pliku: {e}")

"""Sekcja główna: tabela km – stacja – pociągi"""
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

    # Zbuduj kolumny pociągów (tylko z wybranego arkusza)
    train_numbers = [str(t["train_number"]) for t in trains_active]
    unique_trains = sorted(set(train_numbers), key=lambda x: (''.join(ch for ch in x if ch.isdigit()) == "", x))
    try:
        print("DBG unique_trains:", unique_trains)
    except Exception:
        pass

    # Wiersze bazujemy na mapie stacji z wybranego arkusza, posortowane po km rosnąco
    station_maps = st.session_state.get("station_maps", {})
    active_station_map = station_maps.get(selected_sheet, station_map)
    station_items = sorted(active_station_map.items(), key=lambda kv: kv[1])

    # Zbuduj strukturę: {(station, km): {train_number: time}} tylko dla wybranego arkusza
    cell_map = {}
    for rec in trains_active:
        key = (rec["station"], float(rec["km"]))
        bucket = cell_map.setdefault(key, {})
        bucket[str(rec["train_number"]) ] = rec["time"]

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
    try:
        print("DBG df_view shape:", df_view.shape)
        print("DBG df_view columns:", df_view.columns.tolist())
    except Exception:
        pass
    st.subheader("Tabela: km – stacja – pociągi")
    st.caption(f"Arkusz: {selected_sheet}")

    # Zdarzenia edycji: ukryta kolumna na sygnał dblclick
    EDIT_EVT_COL = "__edit_evt__"
    if EDIT_EVT_COL not in df_view.columns:
        df_view[EDIT_EVT_COL] = ""

    gb = GridOptionsBuilder.from_dataframe(df_view)
    gb.configure_default_column(resizable=True, sortable=False, filter=False)
    gb.configure_column("km", header_name="km", editable=False, width=90)
    gb.configure_column("stacja", header_name="stacja", editable=False, width=200)
    gb.configure_column(EDIT_EVT_COL, hide=True, editable=False)

    # Event dblclick na komórce: ustaw payload w ukrytej kolumnie
    gb.configure_grid_options(
        onCellDoubleClicked=JsCode(
            """
            function(e){
              try{
                var f = e.colDef.field;
                if (f === 'km' || f === 'stacja' || f === '__edit_evt__') { return; }
                var station = e.data['stacja'];
                var km = e.data['km'];
                var payload = f + '||' + station + '||' + km;
                e.node.setDataValue('__edit_evt__', payload);
              } catch(err){
                console.error(err);
              }
            }
            """
        )
                            )

    grid_options = gb.build()

    # Nonce do wymuszenia resetu siatki po akcji w modalu
    grid_nonce_key = f"grid_nonce_{selected_sheet}"
    if grid_nonce_key not in st.session_state:
        st.session_state[grid_nonce_key] = 0
    grid_resp = AgGrid(
        df_view,
                        gridOptions=grid_options,
                        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
                        enable_enterprise_modules=False,
                        fit_columns_on_grid_load=True,
                        theme="streamlit",
        height=min(600, 100 + 26 * (len(df_view) + 1)),
        key=f"grid_{selected_sheet}_{st.session_state[grid_nonce_key]}",
    )

    # Sprawdź event dblclick
    try:
        df_after = grid_resp["data"] if isinstance(grid_resp.get("data"), pd.DataFrame) else pd.DataFrame(grid_resp.get("data", []))
    except Exception:
        df_after = df_view

    evt_rows = df_after[df_after[EDIT_EVT_COL].astype(str) != ""] if EDIT_EVT_COL in df_after.columns else pd.DataFrame()
    if not evt_rows.empty:
        first_evt = str(evt_rows.iloc[0][EDIT_EVT_COL])
        try:
            col_id, station_clicked, km_str = first_evt.split("||", 2)
            km_clicked = float(str(km_str).replace(",", ".")) if km_str else 0.0
        except Exception:
            col_id, station_clicked, km_clicked = "", "", 0.0

        # Ustal domyślną godzinę z danych
        current_time_str = cell_map.get((station_clicked, float(km_clicked)), {}).get(col_id, "")
        try:
            print("DBG dblclick col=", col_id, "station=", station_clicked, "km=", km_clicked, "current=", current_time_str)
        except Exception:
            pass
        parsed = parse_time(current_time_str) if current_time_str else None
        default_time = dt.time(int(parsed) % 24, int(round((parsed % 1) * 60))) if parsed is not None else dt.time(0, 0)

        # Modal dialog edycji czasu (wymaga Streamlit 1.34+)
        try:
            @st.experimental_dialog("Edycja czasu")
            def time_dialog():
                st.write(f"Stacja: {station_clicked}  •  km: {km_clicked:.3f}  •  Pociąg: {col_id}")
                t = st.time_input("Godzina", value=default_time, step=dt.timedelta(minutes=1), key=f"dlg_time_{selected_sheet}")
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    if st.button("Zapisz", type="primary", key=f"dlg_save_{selected_sheet}"):
                        try:
                            print("DBG save clicked: col=", col_id, "station=", station_clicked, "km=", km_clicked, "time=", t)
                        except Exception:
                            pass
                        save_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, t, st.session_state)
                        st.session_state[grid_nonce_key] += 1
                        try:
                            print("DBG nonce after save:", st.session_state[grid_nonce_key])
                        except Exception:
                            pass
                        st.rerun()
                with c2:
                    if st.button("Wyczyść", key=f"dlg_clear_{selected_sheet}"):
                        try:
                            print("DBG clear clicked: col=", col_id, "station=", station_clicked, "km=", km_clicked)
                        except Exception:
                            pass
                        clear_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, st.session_state)
                        st.session_state[grid_nonce_key] += 1
                        try:
                            print("DBG nonce after clear:", st.session_state[grid_nonce_key])
                        except Exception:
                            pass
                        st.rerun()
                with c3:
                    if st.button("Cofnij", key=f"dlg_cancel_{selected_sheet}"):
                        st.session_state[grid_nonce_key] += 1
                        try:
                            print("DBG cancel clicked; nonce:", st.session_state[grid_nonce_key])
                        except Exception:
                            pass
                        st.rerun()

            time_dialog()
        except Exception:
            # Fallback: pokaż wbudowany panel zamiast modala
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
                    if st.button("Wyczyść", key=f"fallback_clear_{selected_sheet}"):
                        clear_cell_time(selected_sheet, station_clicked, float(km_clicked), col_id, st.session_state)
                        st.session_state[grid_nonce_key] += 1
                        st.rerun()
                with c3:
                    if st.button("Cofnij", key=f"fallback_cancel_{selected_sheet}"):
                        st.session_state[grid_nonce_key] += 1
                        st.rerun()
else:
    st.info("Brak danych do zbudowania tabeli. Wczytaj plik.")

st.markdown("---")

# Debugowy podgląd danych zapisanych w stanie aplikacji
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
