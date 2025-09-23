import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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

st.title("📊 Wykres rozkładu jazdy pociągów (AgGrid - klikalne nagłówki)")

uploaded_file = st.file_uploader("Prześlij plik Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    # Get reference station list from first sheet
    first_sheet = xls.sheet_names[0]
    df_first = pd.read_excel(uploaded_file, sheet_name=first_sheet, header=None, dtype=str)
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
    all_paths = {}
    sheet_tables = []  # list of (sheet_name, DataFrame)

    for sheet in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name=sheet, header=None, dtype=str)
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

        train_columns = extract_train_columns(
            df,
            pos["train_row"],
            station_start_row=pos.get("station_start_row"),
            station_end_row=pos.get("station_end_row"),
        )

        # Use reference km values when creating paths
        paths = extract_train_paths(
            df,
            [(station_to_km[s], s, r) for _, s, r in stations],
            train_columns,
        )
        all_paths.update(paths)

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

    # Build interactive chart
    if all_paths:
        all_times = [t for pts in all_paths.values() for t, _, _ in pts]
        min_time = min(all_times) - 0.25
        max_time = max(all_times) + 0.25

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

        if "highlighted_train" not in st.session_state:
            st.session_state.highlighted_train = None

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

        # Show tables with AgGrid
        for sheet_name, table in sheet_tables:
            st.markdown(f"### Arkusz: {sheet_name}")

            gb = GridOptionsBuilder.from_dataframe(table)
            gb.configure_default_column(resizable=True, filter=False, sortable=False)

            if "km" in table.columns:
                gb.configure_column("km", header_name="km", type=["numericColumn"], width=90)
            if "station" in table.columns:
                gb.configure_column("station", header_name="stacja", width=200)

            # train columns: clickable headers, no sort/filter
            for col in table.columns:
                if col not in ("km", "station"):
                    gb.configure_column(
                        col,
                        header_name=str(col),
                        sortable=False,
                        filter=False,
                        suppressMenu=True,
                        headerTooltip=f"Kliknij nagłówek aby podświetlić pociąg {col}",
                    )

            grid_options = gb.build()

            grid_response = AgGrid(
                table,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.NO_UPDATE,
                allow_unsafe_jscode=True,
                enable_enterprise_modules=False,
                fit_columns_on_grid_load=True,
                theme="streamlit",
                height=400,
            )

            columns_state = grid_response.get("columns_state") or []
            if isinstance(columns_state, list):
                for state in columns_state:
                    if state.get("colId") not in ("km", "station"):
                        # jeśli w stanie pojawi się 'sort', traktujemy to jako kliknięcie nagłówka
                        if state.get("sort") is not None:
                            clicked_col = state["colId"]
                            if st.session_state.highlighted_train == clicked_col:
                                st.session_state.highlighted_train = None
                            else:
                                st.session_state.highlighted_train = clicked_col
                            st.rerun()
    else:
        st.info("Nie znaleziono ścieżek pociągów w przesłanym pliku.")
