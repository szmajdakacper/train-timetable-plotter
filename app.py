import streamlit as st

from excel_loader import read_and_store_in_session


st.set_page_config(layout="wide", page_title="Train timetable debug")

st.title("🧪 Debug: Excel → session state")

uploaded_file = st.file_uploader("Prześlij plik Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.getvalue()
        read_and_store_in_session(file_bytes, st.session_state)
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
            label="",
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
    st.subheader("Tabela: km – stacja – pociągi")
    st.caption(f"Arkusz: {selected_sheet}")
    st.dataframe(df_view, use_container_width=True)
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
