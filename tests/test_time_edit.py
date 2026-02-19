"""Comprehensive tests for the time editing flow.

Tests cover:
- save_cell_time / clear_cell_time / propagate_time_shift directly
- The FastAPI endpoint logic (delta computation, canonical km lookup)
- Edge cases: dual stations (p/o), day offset, midnight crossing,
  direction detection, cross-sheet editing, first/middle/last station
"""

import copy
import datetime as dt
import pytest

from backend.models.session import SessionState
from table_editor import save_cell_time, clear_cell_time, propagate_time_shift
from utils import format_time_decimal, format_time_hhmm


# ---------------------------------------------------------------------------
# Fixtures — reusable session data
# ---------------------------------------------------------------------------

def _make_train_rec(train_number: str, station: str, km: float,
                    time_decimal: float, stop_type: str | None = None) -> dict:
    rec = {
        "train_number": train_number,
        "station": station,
        "km": km,
        "time": format_time_decimal(time_decimal),
        "time_decimal": time_decimal,
    }
    if stop_type is not None:
        rec["stop_type"] = stop_type
    return rec


def _ascending_train_session() -> SessionState:
    """Train 101 going km 0→10→20→30→40, times 6:00→6:30→7:00→7:30→8:00."""
    session = SessionState()
    session["sheets_data"] = [{
        "sheet": "WL",
        "trains": [
            _make_train_rec("101", "A", 0.0, 6.0),
            _make_train_rec("101", "B", 10.0, 6.5),
            _make_train_rec("101", "C", 20.0, 7.0),
            _make_train_rec("101", "D", 30.0, 7.5),
            _make_train_rec("101", "E", 40.0, 8.0),
        ],
    }]
    session["station_map"] = {"A": 0, "B": 10, "C": 20, "D": 30, "E": 40}
    session["station_maps"] = {"WL": {"A": 0, "B": 10, "C": 20, "D": 30, "E": 40}}
    session["selected_sheet"] = "WL"
    session["train_colors"] = {}
    return session


def _descending_train_session() -> SessionState:
    """Train 202 going km 40→30→20→10→0, times 10:00→10:30→11:00→11:30→12:00."""
    session = SessionState()
    session["sheets_data"] = [{
        "sheet": "LW",
        "trains": [
            _make_train_rec("202", "E", 40.0, 10.0),
            _make_train_rec("202", "D", 30.0, 10.5),
            _make_train_rec("202", "C", 20.0, 11.0),
            _make_train_rec("202", "B", 10.0, 11.5),
            _make_train_rec("202", "A", 0.0, 12.0),
        ],
    }]
    session["station_map"] = {"A": 0, "B": 10, "C": 20, "D": 30, "E": 40}
    session["station_maps"] = {"LW": {"A": 0, "B": 10, "C": 20, "D": 30, "E": 40}}
    session["selected_sheet"] = "LW"
    session["train_colors"] = {}
    return session


def _dual_station_session() -> SessionState:
    """Train 301 with dual station at B (arrival p + departure o)."""
    session = SessionState()
    session["sheets_data"] = [{
        "sheet": "S1",
        "trains": [
            _make_train_rec("301", "A", 0.0, 6.0),
            _make_train_rec("301", "B", 10.0, 6.5, stop_type="p"),
            _make_train_rec("301", "B", 10.0, 6.6, stop_type="o"),
            _make_train_rec("301", "C", 20.0, 7.0),
        ],
    }]
    session["station_map"] = {"A": 0, "B": 10, "C": 20}
    session["station_maps"] = {"S1": {"A": 0, "B": 10, "C": 20}}
    session["selected_sheet"] = "S1"
    session["train_colors"] = {}
    return session


def _two_sheet_session() -> SessionState:
    """Two sheets with different km for same stations."""
    session = SessionState()
    session["sheets_data"] = [
        {
            "sheet": "WL",
            "trains": [
                _make_train_rec("101", "Legnica", 0.0, 6.0),
                _make_train_rec("101", "Jawor", 20.0, 6.5),
                _make_train_rec("101", "Wroclaw", 65.0, 8.0),
            ],
        },
        {
            "sheet": "LW",
            "trains": [
                _make_train_rec("202", "Wroclaw", 0.0, 10.0),
                _make_train_rec("202", "Jawor", 45.0, 11.5),
                _make_train_rec("202", "Legnica", 65.0, 12.0),
            ],
        },
    ]
    session["station_map"] = {"Legnica": 0, "Jawor": 20, "Wroclaw": 65}
    session["station_maps"] = {
        "WL": {"Legnica": 0, "Jawor": 20, "Wroclaw": 65},
        "LW": {"Wroclaw": 0, "Jawor": 45, "Legnica": 65},
    }
    session["selected_sheet"] = "WL"
    session["train_colors"] = {}
    return session


def _midnight_crossing_session() -> SessionState:
    """Train 401 crossing midnight: 23:00 → 23:30 → 0:30(+1) → 1:00(+1)."""
    session = SessionState()
    session["sheets_data"] = [{
        "sheet": "N1",
        "trains": [
            _make_train_rec("401", "A", 0.0, 23.0),
            _make_train_rec("401", "B", 10.0, 23.5),
            _make_train_rec("401", "C", 20.0, 24.5),   # 0:30 (+1)
            _make_train_rec("401", "D", 30.0, 25.0),   # 1:00 (+1)
        ],
    }]
    session["station_map"] = {"A": 0, "B": 10, "C": 20, "D": 30}
    session["station_maps"] = {"N1": {"A": 0, "B": 10, "C": 20, "D": 30}}
    session["selected_sheet"] = "N1"
    session["train_colors"] = {}
    return session


def _get_train_times(session: SessionState, sheet: str, train: str) -> dict[str, float]:
    """Return {station: time_decimal} for quick assertions."""
    for entry in session.get("sheets_data", []):
        if entry["sheet"] == sheet:
            result = {}
            for r in entry["trains"]:
                if str(r["train_number"]) == train:
                    key = r["station"]
                    if r.get("stop_type"):
                        key += f"_{r['stop_type']}"
                    result[key] = r["time_decimal"]
            return result
    return {}


# ---------------------------------------------------------------------------
# 1) save_cell_time — basic
# ---------------------------------------------------------------------------

class TestSaveCellTime:
    def test_update_existing(self):
        session = _ascending_train_session()
        save_cell_time("WL", "C", 20.0, "101", dt.time(7, 15), session)
        times = _get_train_times(session, "WL", "101")
        assert abs(times["C"] - 7.25) < 0.001

    def test_create_new_record(self):
        session = _ascending_train_session()
        save_cell_time("WL", "F", 50.0, "101", dt.time(9, 0), session)
        times = _get_train_times(session, "WL", "101")
        assert "F" in times
        assert abs(times["F"] - 9.0) < 0.001

    def test_day_offset(self):
        session = _ascending_train_session()
        save_cell_time("WL", "A", 0.0, "101", dt.time(1, 0), session, day_offset=1)
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 25.0) < 0.001  # 1:00 + 24h

    def test_dual_station_arrival(self):
        session = _dual_station_session()
        save_cell_time("S1", "B", 10.0, "301", dt.time(6, 40), session, stop_type="p")
        times = _get_train_times(session, "S1", "301")
        assert abs(times["B_p"] - (6 + 40 / 60)) < 0.001

    def test_dual_station_departure(self):
        session = _dual_station_session()
        save_cell_time("S1", "B", 10.0, "301", dt.time(6, 50), session, stop_type="o")
        times = _get_train_times(session, "S1", "301")
        assert abs(times["B_o"] - (6 + 50 / 60)) < 0.001

    def test_wrong_sheet_noop(self):
        session = _ascending_train_session()
        original = copy.deepcopy(session.get("sheets_data"))
        save_cell_time("NONEXIST", "A", 0.0, "101", dt.time(9, 0), session)
        assert session.get("sheets_data") == original


# ---------------------------------------------------------------------------
# 2) clear_cell_time
# ---------------------------------------------------------------------------

class TestClearCellTime:
    def test_clear_existing(self):
        session = _ascending_train_session()
        clear_cell_time("WL", "C", 20.0, "101", session)
        times = _get_train_times(session, "WL", "101")
        assert "C" not in times

    def test_clear_nonexistent_is_noop(self):
        session = _ascending_train_session()
        original_count = len(session.get("sheets_data")[0]["trains"])
        clear_cell_time("WL", "Z", 99.0, "101", session)
        assert len(session.get("sheets_data")[0]["trains"]) == original_count

    def test_clear_dual_station_arrival_only(self):
        session = _dual_station_session()
        clear_cell_time("S1", "B", 10.0, "301", session, stop_type="p")
        times = _get_train_times(session, "S1", "301")
        assert "B_p" not in times
        assert "B_o" in times  # departure untouched


# ---------------------------------------------------------------------------
# 3) propagate_time_shift — ascending train
# ---------------------------------------------------------------------------

class TestPropagateAscending:
    def test_shift_from_first_station(self):
        """Edit first station (km=0): should shift all downstream (km>0)."""
        session = _ascending_train_session()
        propagate_time_shift("WL", "101", 0.0, 0.5, session)  # +30min
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001    # NOT shifted (edited station)
        assert abs(times["B"] - 7.0) < 0.001    # 6.5 + 0.5
        assert abs(times["C"] - 7.5) < 0.001    # 7.0 + 0.5
        assert abs(times["D"] - 8.0) < 0.001    # 7.5 + 0.5
        assert abs(times["E"] - 8.5) < 0.001    # 8.0 + 0.5

    def test_shift_from_middle_station(self):
        """Edit middle station (km=20): only km>20 should shift."""
        session = _ascending_train_session()
        propagate_time_shift("WL", "101", 20.0, -0.25, session)  # -15min
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001    # unchanged
        assert abs(times["B"] - 6.5) < 0.001    # unchanged
        assert abs(times["C"] - 7.0) < 0.001    # NOT shifted (from_km)
        assert abs(times["D"] - 7.25) < 0.001   # 7.5 - 0.25
        assert abs(times["E"] - 7.75) < 0.001   # 8.0 - 0.25

    def test_shift_from_last_station(self):
        """Edit last station (km=40): no downstream stations — no changes."""
        session = _ascending_train_session()
        original = _get_train_times(session, "WL", "101")
        propagate_time_shift("WL", "101", 40.0, 1.0, session)
        after = _get_train_times(session, "WL", "101")
        assert after == original

    def test_negative_shift(self):
        """Make a train earlier; downstream should shift earlier too."""
        session = _ascending_train_session()
        propagate_time_shift("WL", "101", 10.0, -1.0, session)  # -1 hour from B
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001    # unchanged
        assert abs(times["B"] - 6.5) < 0.001    # unchanged (from_km)
        assert abs(times["C"] - 6.0) < 0.001    # 7.0 - 1.0
        assert abs(times["D"] - 6.5) < 0.001    # 7.5 - 1.0
        assert abs(times["E"] - 7.0) < 0.001    # 8.0 - 1.0


# ---------------------------------------------------------------------------
# 4) propagate_time_shift — descending train
# ---------------------------------------------------------------------------

class TestPropagateDescending:
    def test_shift_from_first_station(self):
        """Train 202: km 40→0. First station km=40. Downstream = km<40."""
        session = _descending_train_session()
        propagate_time_shift("LW", "202", 40.0, 0.5, session)
        times = _get_train_times(session, "LW", "202")
        assert abs(times["E"] - 10.0) < 0.001   # NOT shifted (from_km)
        assert abs(times["D"] - 11.0) < 0.001   # 10.5 + 0.5
        assert abs(times["C"] - 11.5) < 0.001   # 11.0 + 0.5
        assert abs(times["B"] - 12.0) < 0.001   # 11.5 + 0.5
        assert abs(times["A"] - 12.5) < 0.001   # 12.0 + 0.5

    def test_shift_from_middle_station(self):
        """Train 202: edit at C (km=20). Downstream = km<20 (B, A)."""
        session = _descending_train_session()
        propagate_time_shift("LW", "202", 20.0, 0.25, session)
        times = _get_train_times(session, "LW", "202")
        assert abs(times["E"] - 10.0) < 0.001   # unchanged
        assert abs(times["D"] - 10.5) < 0.001   # unchanged
        assert abs(times["C"] - 11.0) < 0.001   # NOT shifted (from_km)
        assert abs(times["B"] - 11.75) < 0.001  # 11.5 + 0.25
        assert abs(times["A"] - 12.25) < 0.001  # 12.0 + 0.25

    def test_shift_from_last_station(self):
        """Train 202: last station km=0. No downstream → no changes."""
        session = _descending_train_session()
        original = _get_train_times(session, "LW", "202")
        propagate_time_shift("LW", "202", 0.0, 1.0, session)
        after = _get_train_times(session, "LW", "202")
        assert after == original


# ---------------------------------------------------------------------------
# 5) propagate with dual stations
# ---------------------------------------------------------------------------

class TestPropagateDualStation:
    def test_shift_arrival_propagates_to_departure_and_beyond(self):
        """Shifting arrival (p) at B should shift departure (o) at B and C."""
        session = _dual_station_session()
        # B_p at km=10. For ascending train, downstream = km>10 which is B_o (same km!) and C.
        # But propagate uses strict inequality (km > from_km), so B_o at same km is NOT shifted.
        propagate_time_shift("S1", "301", 10.0, 0.5, session)
        times = _get_train_times(session, "S1", "301")
        assert abs(times["A"] - 6.0) < 0.001
        # B_p and B_o are both at km=10 = from_km, so NOT shifted
        assert abs(times["B_p"] - 6.5) < 0.001
        assert abs(times["B_o"] - 6.6) < 0.001
        # C at km=20 > 10 → shifted
        assert abs(times["C"] - 7.5) < 0.001

    def test_shift_from_before_dual_station(self):
        """Shifting from A (km=0) should shift B_p, B_o, and C."""
        session = _dual_station_session()
        propagate_time_shift("S1", "301", 0.0, 0.25, session)
        times = _get_train_times(session, "S1", "301")
        assert abs(times["A"] - 6.0) < 0.001
        assert abs(times["B_p"] - 6.75) < 0.001
        assert abs(times["B_o"] - 6.85) < 0.001
        assert abs(times["C"] - 7.25) < 0.001


# ---------------------------------------------------------------------------
# 6) Midnight crossing
# ---------------------------------------------------------------------------

class TestMidnightCrossing:
    def test_propagate_across_midnight(self):
        """Shift at B (23:30), downstream C (0:30+1=24.5) and D (1:00+1=25.0) should shift."""
        session = _midnight_crossing_session()
        propagate_time_shift("N1", "401", 10.0, 0.5, session)
        times = _get_train_times(session, "N1", "401")
        assert abs(times["A"] - 23.0) < 0.001
        assert abs(times["B"] - 23.5) < 0.001
        assert abs(times["C"] - 25.0) < 0.001   # 24.5 + 0.5
        assert abs(times["D"] - 25.5) < 0.001   # 25.0 + 0.5

    def test_direction_detection_across_midnight(self):
        """Direction should still be ascending even though times wrap."""
        session = _midnight_crossing_session()
        # Shift from first station (km=0), all downstream should shift
        propagate_time_shift("N1", "401", 0.0, 0.25, session)
        times = _get_train_times(session, "N1", "401")
        assert abs(times["A"] - 23.0) < 0.001
        assert abs(times["B"] - 23.75) < 0.001
        assert abs(times["C"] - 24.75) < 0.001
        assert abs(times["D"] - 25.25) < 0.001


# ---------------------------------------------------------------------------
# 7) Cross-sheet editing — canonical km resolution
# ---------------------------------------------------------------------------

class TestCrossSheetKm:
    def test_canonical_km_from_own_sheet(self):
        """_canonical_km should return the km from the train's own sheet."""
        from backend.routers.edit import _canonical_km
        session = _two_sheet_session()

        # Jawor in WL is at km=20, in LW at km=45
        km_wl = _canonical_km(session, "WL", "Jawor", 45.0)
        assert abs(km_wl - 20.0) < 0.001

        km_lw = _canonical_km(session, "LW", "Jawor", 20.0)
        assert abs(km_lw - 45.0) < 0.001

    def test_propagate_cross_sheet_train(self):
        """Editing train 202 (sheet LW) while viewing WL — km must resolve correctly."""
        session = _two_sheet_session()
        # Train 202 is in sheet LW. LW has km: Wroclaw=0, Jawor=45, Legnica=65
        # It's a descending-km train: starts at Wroclaw km=0, goes to Legnica km=65
        # Wait — that's ascending! Wroclaw=0 at t=10:00, Jawor=45 at t=11:30, Legnica=65 at t=12:00
        # So it IS ascending (km increases with time).

        # Shift from Jawor (km=45 in LW). Downstream = km>45, i.e. Legnica (km=65)
        propagate_time_shift("LW", "202", 45.0, 0.5, session)
        times = _get_train_times(session, "LW", "202")
        assert abs(times["Wroclaw"] - 10.0) < 0.001   # unchanged
        assert abs(times["Jawor"] - 11.5) < 0.001     # from_km, unchanged
        assert abs(times["Legnica"] - 12.5) < 0.001   # 12.0 + 0.5


# ---------------------------------------------------------------------------
# 8) Backend delta computation (simulating edit.py logic)
# ---------------------------------------------------------------------------

def _compute_delta(old_decimal: float, new_hour: int, new_minute: int, new_second: int = 0) -> float:
    """Replicate the delta computation from edit.py save_time."""
    new_dec = new_hour + new_minute / 60.0 + new_second / 3600.0
    parsed_norm = float(old_decimal) % 24
    delta = new_dec - parsed_norm
    if delta > 12:
        delta -= 24
    elif delta < -12:
        delta += 24
    return delta


class TestDeltaComputation:
    def test_simple_forward(self):
        """7:00 → 7:30 = +0.5h"""
        delta = _compute_delta(7.0, 7, 30)
        assert abs(delta - 0.5) < 0.001

    def test_simple_backward(self):
        """7:00 → 6:30 = -0.5h"""
        delta = _compute_delta(7.0, 6, 30)
        assert abs(delta - (-0.5)) < 0.001

    def test_near_midnight_forward(self):
        """23:30 → 0:15 should be +0.75h (not -23.25h)."""
        delta = _compute_delta(23.5, 0, 15)
        assert abs(delta - 0.75) < 0.001

    def test_near_midnight_backward(self):
        """0:30 → 23:45 should be -0.75h (not +23.25h)."""
        delta = _compute_delta(0.5, 23, 45)
        assert abs(delta - (-0.75)) < 0.001

    def test_midnight_wrap_for_day_offset_time(self):
        """old_decimal=24.5 (0:30+1), new time 1:00 → delta = +0.5h.
        Uses old_decimal % 24 = 0.5, new_dec = 1.0 → delta = 0.5."""
        delta = _compute_delta(24.5, 1, 0)
        assert abs(delta - 0.5) < 0.001

    def test_large_negative_wrap(self):
        """old_decimal=25.0 (1:00+1), new time 0:00 → delta = -1.0h.
        old % 24 = 1.0, new_dec = 0.0 → delta = -1.0."""
        delta = _compute_delta(25.0, 0, 0)
        assert abs(delta - (-1.0)) < 0.001

    def test_zero_delta(self):
        """Same time → delta = 0"""
        delta = _compute_delta(14.5, 14, 30)
        assert abs(delta) < 0.001

    def test_exactly_12h_forward(self):
        """6:00 → 18:00 = +12h. delta=12 triggers wrap to -12."""
        delta = _compute_delta(6.0, 18, 0)
        # delta = 18 - 6 = 12, which is > 12? No, > 12 is strict.
        # 12.0 > 12 is False, so delta stays 12.0.
        assert abs(delta - 12.0) < 0.001

    def test_just_over_12h(self):
        """6:00 → 18:30 = +12.5h, wraps to -11.5h."""
        delta = _compute_delta(6.0, 18, 30)
        assert abs(delta - (-11.5)) < 0.001


# ---------------------------------------------------------------------------
# 9) Full endpoint simulation — save_time flow
# ---------------------------------------------------------------------------

def _simulate_save_time(session: SessionState, sheet: str, station: str,
                        km_from_frontend: float, train_number: str,
                        hour: int, minute: int, second: int = 0,
                        day_offset: int = 0, stop_type: str | None = None,
                        propagate: bool = False):
    """Simulate what edit.py save_time does."""
    from backend.routers.edit import _canonical_km

    time_value = dt.time(hour, minute, second)
    km = _canonical_km(session, sheet, station, km_from_frontend)

    if propagate:
        sheets_data = session.get("sheets_data", [])
        active = next((s for s in sheets_data if s.get("sheet") == sheet), None)
        old_decimal = None
        if active:
            for rec in active.get("trains", []):
                if (str(rec.get("train_number")) == train_number
                        and rec.get("station") == station
                        and abs(float(rec.get("km", 0)) - km) < 0.01
                        and rec.get("stop_type") == stop_type):
                    old_decimal = rec.get("time_decimal")
                    break
        if old_decimal is not None:
            new_dec = hour + minute / 60.0 + second / 3600.0
            parsed_norm = float(old_decimal) % 24
            delta_hours = new_dec - parsed_norm
            if delta_hours > 12:
                delta_hours -= 24
            elif delta_hours < -12:
                delta_hours += 24
            if delta_hours != 0.0:
                propagate_time_shift(sheet, train_number, km, delta_hours, session)

    save_cell_time(sheet, station, km, train_number, time_value, session,
                   day_offset=day_offset, stop_type=stop_type)


class TestFullSaveFlow:
    def test_edit_ascending_middle_with_propagate(self):
        """Ascending train, edit C (7:00 → 7:15), propagate: D and E shift +15min."""
        session = _ascending_train_session()
        _simulate_save_time(session, "WL", "C", 20.0, "101", 7, 15, propagate=True)
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001
        assert abs(times["B"] - 6.5) < 0.001
        assert abs(times["C"] - 7.25) < 0.001   # updated to 7:15
        assert abs(times["D"] - 7.75) < 0.001   # 7.5 + 0.25
        assert abs(times["E"] - 8.25) < 0.001   # 8.0 + 0.25

    def test_edit_descending_middle_with_propagate(self):
        """Descending train 202, edit C (km=20, 11:00 → 11:30), propagate: B and A shift +30min."""
        session = _descending_train_session()
        _simulate_save_time(session, "LW", "C", 20.0, "202", 11, 30, propagate=True)
        times = _get_train_times(session, "LW", "202")
        assert abs(times["E"] - 10.0) < 0.001   # unchanged
        assert abs(times["D"] - 10.5) < 0.001   # unchanged
        assert abs(times["C"] - 11.5) < 0.001   # updated to 11:30
        assert abs(times["B"] - 12.0) < 0.001   # 11.5 + 0.5
        assert abs(times["A"] - 12.5) < 0.001   # 12.0 + 0.5

    def test_edit_ascending_first_with_propagate(self):
        """Edit first station of ascending train, all downstream shift."""
        session = _ascending_train_session()
        _simulate_save_time(session, "WL", "A", 0.0, "101", 5, 30, propagate=True)
        times = _get_train_times(session, "WL", "101")
        # A was 6:00, now 5:30 → delta = -0.5
        assert abs(times["A"] - 5.5) < 0.001
        assert abs(times["B"] - 6.0) < 0.001    # 6.5 - 0.5
        assert abs(times["C"] - 6.5) < 0.001    # 7.0 - 0.5
        assert abs(times["D"] - 7.0) < 0.001    # 7.5 - 0.5
        assert abs(times["E"] - 7.5) < 0.001    # 8.0 - 0.5

    def test_edit_ascending_last_with_propagate(self):
        """Edit last station of ascending train — nothing downstream to shift."""
        session = _ascending_train_session()
        _simulate_save_time(session, "WL", "E", 40.0, "101", 9, 0, propagate=True)
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001
        assert abs(times["B"] - 6.5) < 0.001
        assert abs(times["C"] - 7.0) < 0.001
        assert abs(times["D"] - 7.5) < 0.001
        assert abs(times["E"] - 9.0) < 0.001    # only this changed

    def test_edit_without_propagate(self):
        """Without propagate, only the edited cell changes."""
        session = _ascending_train_session()
        _simulate_save_time(session, "WL", "C", 20.0, "101", 8, 0, propagate=False)
        times = _get_train_times(session, "WL", "101")
        assert abs(times["A"] - 6.0) < 0.001
        assert abs(times["B"] - 6.5) < 0.001
        assert abs(times["C"] - 8.0) < 0.001    # only this changed
        assert abs(times["D"] - 7.5) < 0.001    # unchanged
        assert abs(times["E"] - 8.0) < 0.001    # unchanged

    def test_edit_descending_first_with_propagate(self):
        """Descending train 202, edit first station E (km=40)."""
        session = _descending_train_session()
        _simulate_save_time(session, "LW", "E", 40.0, "202", 10, 30, propagate=True)
        times = _get_train_times(session, "LW", "202")
        # E was 10:00 → 10:30, delta = +0.5
        assert abs(times["E"] - 10.5) < 0.001
        assert abs(times["D"] - 11.0) < 0.001   # 10.5 + 0.5
        assert abs(times["C"] - 11.5) < 0.001   # 11.0 + 0.5
        assert abs(times["B"] - 12.0) < 0.001   # 11.5 + 0.5
        assert abs(times["A"] - 12.5) < 0.001   # 12.0 + 0.5

    def test_edit_descending_last_with_propagate(self):
        """Descending train 202, edit last station A (km=0) — nothing downstream."""
        session = _descending_train_session()
        _simulate_save_time(session, "LW", "A", 0.0, "202", 13, 0, propagate=True)
        times = _get_train_times(session, "LW", "202")
        assert abs(times["E"] - 10.0) < 0.001
        assert abs(times["D"] - 10.5) < 0.001
        assert abs(times["C"] - 11.0) < 0.001
        assert abs(times["B"] - 11.5) < 0.001
        assert abs(times["A"] - 13.0) < 0.001

    def test_edit_cross_sheet_with_wrong_km(self):
        """Editing train 202 (LW) while viewing WL — frontend sends WL's km.
        _canonical_km should resolve to LW's km."""
        session = _two_sheet_session()
        # Frontend sends km for Jawor from WL's map (20.0)
        # but train 202 is in LW where Jawor = 45.0
        _simulate_save_time(session, "LW", "Jawor", 20.0, "202", 12, 0, propagate=True)
        times = _get_train_times(session, "LW", "202")
        # Jawor was 11:30, now 12:00, delta = +0.5
        # Downstream for ascending = km > 45 → Legnica (km=65)
        assert abs(times["Wroclaw"] - 10.0) < 0.001
        assert abs(times["Jawor"] - 12.0) < 0.001
        assert abs(times["Legnica"] - 12.5) < 0.001

    def test_midnight_crossing_edit_with_propagate(self):
        """Edit B (23:30 → 23:45), downstream C and D shift +15min."""
        session = _midnight_crossing_session()
        _simulate_save_time(session, "N1", "B", 10.0, "401", 23, 45, propagate=True)
        times = _get_train_times(session, "N1", "401")
        assert abs(times["A"] - 23.0) < 0.001
        assert abs(times["B"] - 23.75) < 0.001    # updated
        assert abs(times["C"] - 24.75) < 0.001    # 24.5 + 0.25
        assert abs(times["D"] - 25.25) < 0.001    # 25.0 + 0.25

    def test_dual_station_edit_arrival_with_propagate(self):
        """Edit arrival (p) at dual station B. Departure (o) at same km is NOT downstream.
        Only C (km=20 > 10) should shift."""
        session = _dual_station_session()
        # B_p was 6:30, change to 6:45, delta = +0.25
        _simulate_save_time(session, "S1", "B", 10.0, "301", 6, 45,
                            stop_type="p", propagate=True)
        times = _get_train_times(session, "S1", "301")
        assert abs(times["A"] - 6.0) < 0.001
        assert abs(times["B_p"] - 6.75) < 0.001   # updated to 6:45
        # B_o at same km=10 is NOT shifted (km <= from_km)
        assert abs(times["B_o"] - 6.6) < 0.001
        assert abs(times["C"] - 7.25) < 0.001     # 7.0 + 0.25


# ---------------------------------------------------------------------------
# 10) Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_station_train(self):
        """Train with only one record — no direction, no propagation."""
        session = SessionState()
        session["sheets_data"] = [{
            "sheet": "S",
            "trains": [_make_train_rec("999", "X", 5.0, 12.0)],
        }]
        session["station_map"] = {"X": 5}
        session["station_maps"] = {"S": {"X": 5}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}
        propagate_time_shift("S", "999", 5.0, 1.0, session)
        times = _get_train_times(session, "S", "999")
        assert abs(times["X"] - 12.0) < 0.001  # unchanged (< 2 records)

    def test_two_station_train_ascending(self):
        """Train with exactly two stations — should still detect direction."""
        session = SessionState()
        session["sheets_data"] = [{
            "sheet": "S",
            "trains": [
                _make_train_rec("50", "P", 0.0, 8.0),
                _make_train_rec("50", "Q", 30.0, 9.0),
            ],
        }]
        session["station_map"] = {"P": 0, "Q": 30}
        session["station_maps"] = {"S": {"P": 0, "Q": 30}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}
        propagate_time_shift("S", "50", 0.0, 0.5, session)
        times = _get_train_times(session, "S", "50")
        assert abs(times["P"] - 8.0) < 0.001
        assert abs(times["Q"] - 9.5) < 0.001

    def test_propagate_does_not_affect_other_trains(self):
        """Another train on the same sheet should be untouched."""
        session = _ascending_train_session()
        # Add a second train
        session.get("sheets_data")[0]["trains"].append(
            _make_train_rec("102", "C", 20.0, 12.0)
        )
        propagate_time_shift("WL", "101", 0.0, 1.0, session)
        times_102 = _get_train_times(session, "WL", "102")
        assert abs(times_102["C"] - 12.0) < 0.001  # unchanged

    def test_negative_time_wraps_to_positive(self):
        """If shift results in negative time_decimal, it wraps via % 24."""
        session = SessionState()
        session["sheets_data"] = [{
            "sheet": "S",
            "trains": [
                _make_train_rec("70", "A", 0.0, 1.0),
                _make_train_rec("70", "B", 10.0, 1.5),
                _make_train_rec("70", "C", 20.0, 2.0),
            ],
        }]
        session["station_map"] = {"A": 0, "B": 10, "C": 20}
        session["station_maps"] = {"S": {"A": 0, "B": 10, "C": 20}}
        session["selected_sheet"] = "S"
        session["train_colors"] = {}
        # Shift B and C by -3 hours → C goes to -1.0 → should wrap to 23.0
        propagate_time_shift("S", "70", 0.0, -3.0, session)
        times = _get_train_times(session, "S", "70")
        assert abs(times["A"] - 1.0) < 0.001
        assert times["B"] >= 0  # should not be negative
        assert times["C"] >= 0

    def test_format_functions_consistency(self):
        """format_time_decimal and format_time_hhmm should be consistent."""
        assert format_time_hhmm(7.5) == "07:30"
        assert format_time_hhmm(0.0) == "00:00"
        assert format_time_hhmm(23.75) == "23:45"
        assert format_time_decimal(25.5) == "01:30 (+1)"
        assert format_time_decimal(48.0) == "00:00 (+2)"
        assert format_time_decimal(-1.0) == "23:00"
