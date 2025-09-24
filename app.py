import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import io

from utils import (
    find_headers,
    extract_stations,
    extract_train_columns,
    extract_train_paths,
    format_time_decimal,
    parse_time,
)

# Set page config to wide mode
st.set_page_config(layout="wide", page_title="Wykres rozkładu jazdy")

st.title("📊 Wykres rozkładu jazdy pociągów")

with st.sidebar:
    st.header("Ustawienia")
    debug = st.checkbox("Tryb debug", value=False, help="Wypisz dodatkowe logi w konsoli serwera.")

@st.cache_data(show_spinner=False)
def read_workbook(file_bytes: bytes):
    """Wczytaj wszystkie arkusze z XLSX jako słownik {nazwa: DataFrame}."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    sheets = {}
    for sheet in xls.sheet_names:
        # Dla spójności z istniejącą logiką trzymamy dtype=str
        sheets[sheet] = xls.parse(sheet_name=sheet, header=None, dtype=str)
    return xls.sheet_names, sheets

uploaded_file = st.file_uploader("Prześlij plik Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.getvalue()
        sheet_names, sheets = read_workbook(file_bytes)
    except Exception as e:
        st.error(f"Nie udało się wczytać pliku: {e}")
        st.stop()

    # Get reference station list from first sheet
    first_sheet = sheet_names[0]
    df_first = sheets[first_sheet]
    pos_first = find_headers(df_first)

    if not all(pos_first[k] is not None for k in ("station_start_row", "station_end_row", "station_col", "km_col")):
        st.error("Brakuje nagłówków stacji w pierwszym arkuszu.")
        st.stop()

    reference_stations = extract_stations(
        df_first,
        start_row=pos_first["station_start_row"],
        end_row=pos_first["station_end_row"],
        station_col=pos_first["station_col"],
        km_col=pos_first["km_col"],
    )

    # Create reference station to km mapping
    station_to_km = {station: km for km, station, _ in reference_stations}
    sheet_tables = []  # list of (sheet_name, DataFrame)

    for sheet in sheet_names:
        df = sheets[sheet]
        pos = find_headers(df)

        if all(pos[k] is not None for k in ("station_start_row", "station_end_row", "station_col", "km_col")):
            stations = extract_stations(
                df,
                start_row=pos["station_start_row"],
                end_row=pos["station_end_row"],
                station_col=pos["station_col"],
                km_col=pos["km_col"],
            )

            # Verify stations match reference
            sheet_stations = {s for _, s, _ in stations}
            if not all(s in station_to_km for s in sheet_stations):
                missing = [s for s in sheet_stations if s not in station_to_km]
                st.error(f"Arkusz '{sheet}' zawiera stacje, które nie występują w referencji: {missing}")
                continue
        else:
            st.error("Brakuje nagłówków stacji.")
            continue

        if pos.get("train_row") is None:
            st.warning(f"Arkusz '{sheet}' nie zawiera wiersza z nagłówkiem 'Numer pociągu'.")
            continue

        train_columns = extract_train_columns(
            df,
            pos["train_row"],
            station_start_row=pos.get("station_start_row"),
            station_end_row=pos.get("station_end_row"),
        )

        # Build table for this sheet
        table_data = []
        for km, station, row in stations:
            row_data = {"km": f"{km:.3f}", "station": station}
            for train_nr, col in train_columns.items():
                val = df.iat[row, col]
                if not pd.isna(val):
                    time_val = parse_time(val)
                    if time_val is not None:
                        row_data[train_nr] = format_time_decimal(time_val)
                    else:
                        row_data[train_nr] = str(val).strip()
                else:
                    row_data[train_nr] = ""
            table_data.append(row_data)

        sheet_table = pd.DataFrame(table_data)
        sheet_tables.append((sheet, sheet_table))

    # Initialize or update editable tables in session state
    if "tables_by_sheet" not in st.session_state:
        st.session_state.tables_by_sheet = {name: table.copy() for name, table in sheet_tables}
    else:
        # ensure all sheets exist in state (new upload or new sheet names)
        for name, table in sheet_tables:
            if name not in st.session_state.tables_by_sheet:
                st.session_state.tables_by_sheet[name] = table.copy()

    # Helper: build paths from edited tables
    def build_paths_from_tables(tables_dict):
        combined = {}
        for name, table in tables_dict.items():
            if table is None or table.empty:
                continue
            # Identify train columns
            train_cols = [c for c in table.columns if c not in ("km", "station")]
            for train_nr in train_cols:
                points = []
                base_time = None
                for _, rec in table.iterrows():
                    station_name = rec.get("station")
                    val = rec.get(train_nr)
                    if pd.isna(station_name):
                        continue
                    # Y: korzystaj zawsze z mapy referencyjnej, nie z edytowanej kolumny 'km'
                    km_val = station_to_km.get(str(station_name))
                    if km_val is None:
                        # pomiń wiersze ze stacjami spoza referencji
                        continue
                    t = parse_time(val)
                    if t is None:
                        continue
                    if base_time is None:
                        base_time = t
                        adj = t
                    else:
                        if t < base_time and (base_time - t) > 12:
                            adj = t + 24
                        else:
                            adj = t
                        if t > base_time and (t - base_time) > 12:
                            base_time = t
                    points.append((adj, km_val, station_name))
                if points:
                    combined[train_nr] = points
        return combined

    # Render tables first (editable) and persist changes, so the plot uses fresh data in the same rerun
    if sheet_tables:
        tabs = st.tabs([f"Arkusz: {name}" for name, _ in sheet_tables])
        for (sheet_name, orig_table), tab in zip(sheet_tables, tabs):
            with tab:
                table = st.session_state.tables_by_sheet.get(sheet_name, orig_table)
                gb = GridOptionsBuilder.from_dataframe(table)
                gb.configure_default_column(resizable=True, filter=False, sortable=False)

                if "km" in table.columns:
                    gb.configure_column("km", header_name="km", type=["numericColumn"], width=90)
                if "station" in table.columns:
                    gb.configure_column("station", header_name="stacja", width=200)

                for col in table.columns:
                    if col not in ("km", "station"):
                        gb.configure_column(
                            col,
                            header_name=str(col),
                            sortable=False,
                            filter=False,
                            suppressMenu=True,
                            editable=True,
                            headerTooltip=f"Edytuj czas (np. 06:35, 6.35, 0.25)",
                        )

                grid_options = gb.build()

                grid_key = f"grid_{sheet_name}"
                grid_response = AgGrid(
                    table,
                    gridOptions=grid_options,
                    data_return_mode=DataReturnMode.AS_INPUT,
                    update_mode=GridUpdateMode.VALUE_CHANGED,
                    allow_unsafe_jscode=False,
                    enable_enterprise_modules=False,
                    fit_columns_on_grid_load=True,
                    theme="streamlit",
                    height=400,
                    key=grid_key,
                )

                if isinstance(grid_response, dict) and grid_response.get("data") is not None:
                    try:
                        new_df = pd.DataFrame(grid_response["data"])  # type: ignore
                        prev_df = st.session_state.tables_by_sheet.get(sheet_name, table)
                        if not isinstance(prev_df, pd.DataFrame) or not new_df.equals(prev_df):
                            st.session_state.tables_by_sheet[sheet_name] = new_df
                            st.rerun()
                    except Exception:
                        pass

    # Build interactive chart from current (possibly edited) tables
    all_paths = build_paths_from_tables(st.session_state.tables_by_sheet)
    if all_paths:
        all_times = [t for pts in all_paths.values() for t, _, _ in pts]
        min_time = min(all_times) - 0.25
        max_time = max(all_times) + 0.25

        # UI: wybór pociągu do podświetlenia (bogatsza etykieta w selectboxie)
        if "highlighted_train" not in st.session_state:
            st.session_state.highlighted_train = None
        train_ids = sorted(all_paths.keys())

        def _format_train_option(opt):
            if opt is None:
                return "(brak)"
            pts = all_paths.get(opt, [])
            if not pts:
                return str(opt)
            first_t, _, first_station = pts[0]
            last_t, _, last_station = pts[-1]
            return f"{opt} — {format_time_decimal(first_t)} {first_station} → {format_time_decimal(last_t)} {last_station}"

        # Inicjalizacja kontrolki tylko raz; wartość bazowa to identyfikator pociągu (lub None)
        if "highlighted_train_select" not in st.session_state:
            st.session_state.highlighted_train_select = (
                st.session_state.highlighted_train if st.session_state.highlighted_train in train_ids else None
            )
        selected_value = st.selectbox(
            "Podświetl pociąg",
            options=[None] + train_ids,
            key="highlighted_train_select",
            format_func=_format_train_option,
        )
        st.session_state.highlighted_train = selected_value

        fig = go.Figure()
        for train_nr, pts in all_paths.items():
            xs = [t for t, _, _ in pts]
            ys = [km for _, km, _ in pts]
            hover_text = [
                f"Pociąg: {train_nr}<br>Czas: {format_time_decimal(t)}<br>Stacja: {s}<br>km: {km}"
                for t, km, s in pts
            ]
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines+markers",
                    name=train_nr,
                    text=hover_text,
                    hoverinfo="text",
                )
            )

        # Use reference stations for Y axis
        station_items = sorted(station_to_km.items(), key=lambda x: x[1])
        station_names = [name for name, _ in station_items]
        station_kms = [km for _, km in station_items]

        fig.update_layout(
            title="Interaktywny rozkład jazdy",
            xaxis=dict(title="Czas [h]", range=[min_time, max_time], gridcolor="lightgray"),
            yaxis=dict(
                title="km",
                autorange="reversed",
                tickmode="array",
                tickvals=station_kms,
                ticktext=station_names,
                gridcolor="lightgray",
                gridwidth=1,
                griddash="dot",
                showgrid=True,
            ),
            height=800,
            margin=dict(l=200, r=50, t=50, b=50),
            plot_bgcolor="white",
            autosize=True,
            dragmode='pan',
        )

        # Plot
        updated_fig = go.Figure(fig)
        if st.session_state.highlighted_train:
            for trace in updated_fig.data:
                if trace.name == st.session_state.highlighted_train:
                    trace.line.width = 4
                    trace.line.color = "red"
                    trace.marker.size = 10
                    trace.opacity = 1.0
                else:
                    trace.line.width = 2
                    trace.opacity = 0.25

        st.plotly_chart(
            updated_fig,
            use_container_width=True,
            config={"displayModeBar": True, "responsive": True},
        )

        # Show tables with AgGrid in tabs (editable time cells)
        if sheet_tables:
            tabs = st.tabs([f"Arkusz: {name}" for name, _ in sheet_tables])
            for (sheet_name, orig_table), tab in zip(sheet_tables, tabs):
                with tab:
                    # Use edited table from session, fallback to original
                    table = st.session_state.tables_by_sheet.get(sheet_name, orig_table)
                    gb = GridOptionsBuilder.from_dataframe(table)
                    gb.configure_default_column(resizable=True, filter=False, sortable=False)

                    if "km" in table.columns:
                        gb.configure_column("km", header_name="km", type=["numericColumn"], width=90)
                    if "station" in table.columns:
                        gb.configure_column("station", header_name="stacja", width=200)

                    # Kolumny pociągów: włącz edycję czasu
                    for col in table.columns:
                        if col not in ("km", "station"):
                            gb.configure_column(
                                col,
                                header_name=str(col),
                                sortable=False,
                                filter=False,
                                suppressMenu=True,
                                editable=True,
                                headerTooltip=f"Edytuj czas (np. 06:35, 6.35, 0.25)",
                            )

                    grid_options = gb.build()

                    grid_key = f"grid_{sheet_name}"
                    grid_response = AgGrid(
                        table,
                        gridOptions=grid_options,
                        update_mode=GridUpdateMode.MODEL_CHANGED,
                        allow_unsafe_jscode=False,
                        enable_enterprise_modules=False,
                        fit_columns_on_grid_load=True,
                        theme="streamlit",
                        height=400,
                        key=grid_key,
                    )

                    # Zapisz zedytowaną tabelę do session_state (jeśli dostępna)
                    if isinstance(grid_response, dict) and grid_response.get("data") is not None:
                        try:
                            st.session_state.tables_by_sheet[sheet_name] = pd.DataFrame(grid_response["data"])  # type: ignore
                            # Po edycji Streamlit wykona rerun, a wykres zostanie odbudowany z nowych danych
                        except Exception:
                            pass
    else:
        st.info("Nie znaleziono ścieżek pociągów w przesłanym pliku.")
