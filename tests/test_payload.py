"""Tests for build_trains_payload — verifying _decimals in grid rows
and stopType in plot point data."""

import pytest
from backend.models.session import SessionState
from backend.services.plot_data import build_trains_payload
from utils import format_time_decimal


def _make_rec(tn, station, km, tdec, stop_type=None):
    rec = {
        "train_number": tn, "station": station, "km": km,
        "time": format_time_decimal(tdec), "time_decimal": tdec,
    }
    if stop_type is not None:
        rec["stop_type"] = stop_type
    return rec


class TestGridDecimals:
    def test_decimals_present(self):
        session = SessionState()
        session["sheets_data"] = [{"sheet": "S", "trains": [
            _make_rec("101", "A", 0.0, 6.5),
            _make_rec("101", "B", 10.0, 7.0),
        ]}]
        session["station_map"] = {"A": 0, "B": 10}
        session["station_maps"] = {"S": {"A": 0, "B": 10}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        rows = payload["grid_rows"]
        assert len(rows) == 2
        assert "_decimals" in rows[0]
        assert abs(rows[0]["_decimals"]["101"] - 6.5) < 0.001
        assert abs(rows[1]["_decimals"]["101"] - 7.0) < 0.001

    def test_decimals_midnight_crossing(self):
        session = SessionState()
        session["sheets_data"] = [{"sheet": "S", "trains": [
            _make_rec("401", "A", 0.0, 23.5),
            _make_rec("401", "B", 10.0, 25.0),  # 1:00 (+1)
        ]}]
        session["station_map"] = {"A": 0, "B": 10}
        session["station_maps"] = {"S": {"A": 0, "B": 10}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        rows = payload["grid_rows"]
        # raw decimal for B should be 25.0 (preserving day offset)
        assert abs(rows[1]["_decimals"]["401"] - 25.0) < 0.001

    def test_decimals_dual_station(self):
        session = SessionState()
        session["sheets_data"] = [{"sheet": "S", "trains": [
            _make_rec("301", "B", 10.0, 6.5, stop_type="p"),
            _make_rec("301", "B", 10.0, 6.8, stop_type="o"),
        ]}]
        session["station_map"] = {"B": 10}
        session["station_maps"] = {"S": {"B": 10}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        rows = payload["grid_rows"]
        assert len(rows) == 2  # p and o rows
        # p row
        p_row = next(r for r in rows if r["_stop_type"] == "p")
        assert abs(p_row["_decimals"]["301"] - 6.5) < 0.001
        # o row
        o_row = next(r for r in rows if r["_stop_type"] == "o")
        assert abs(o_row["_decimals"]["301"] - 6.8) < 0.001


class TestPlotStopType:
    def test_stopType_in_plot_points(self):
        session = SessionState()
        session["sheets_data"] = [{"sheet": "S", "trains": [
            _make_rec("301", "A", 0.0, 6.0),
            _make_rec("301", "B", 10.0, 6.5, stop_type="p"),
            _make_rec("301", "B", 10.0, 6.8, stop_type="o"),
            _make_rec("301", "C", 20.0, 7.0),
        ]}]
        session["station_map"] = {"A": 0, "B": 10, "C": 20}
        session["station_maps"] = {"S": {"A": 0, "B": 10, "C": 20}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        series = payload["plot_series"]
        assert len(series) == 1

        points = series[0]["points"]
        # Find the two B points
        b_points = [p for p in points if p["station"] == "B"]
        assert len(b_points) == 2
        stop_types = {p["stopType"] for p in b_points}
        assert stop_types == {"p", "o"}

    def test_stopType_none_for_non_dual(self):
        session = SessionState()
        session["sheets_data"] = [{"sheet": "S", "trains": [
            _make_rec("101", "A", 0.0, 6.0),
        ]}]
        session["station_map"] = {"A": 0}
        session["station_maps"] = {"S": {"A": 0}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        points = payload["plot_series"][0]["points"]
        assert points[0]["stopType"] is None

    def test_cross_sheet_plot_has_stopType(self):
        session = SessionState()
        session["sheets_data"] = [
            {"sheet": "WL", "trains": [_make_rec("101", "A", 0.0, 6.0)]},
            {"sheet": "LW", "trains": [
                _make_rec("202", "A", 50.0, 10.0, stop_type="p"),
                _make_rec("202", "A", 50.0, 10.2, stop_type="o"),
            ]},
        ]
        session["station_map"] = {"A": 0}
        session["station_maps"] = {"WL": {"A": 0}, "LW": {"A": 50}}
        session["selected_sheet"] = "WL"
        session["train_colors"] = {}

        payload = build_trains_payload(session)
        # Find series for train 202
        lw_series = [s for s in payload["plot_series"] if "202" in s["name"]]
        assert len(lw_series) == 1
        pts = lw_series[0]["points"]
        stop_types = {p["stopType"] for p in pts}
        assert stop_types == {"p", "o"}
