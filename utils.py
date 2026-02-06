import pandas as pd
from typing import Dict, Optional, Tuple, List, Sequence
import unicodedata
import re

# ===================== Helpers =====================

def normalize(s: str) -> str:
    """Normalize text for header comparison (casefold, collapse spaces, strip accents)."""
    if s is None:
        return ""
    text = str(s).replace("\xa0", " ").strip().lower()
    # collapse internal whitespace
    text = " ".join(text.split())
    # strip accents
    text_nfkd = unicodedata.normalize("NFKD", text)
    text_no_accents = "".join(ch for ch in text_nfkd if not unicodedata.combining(ch))
    return text_no_accents

def parse_km(value) -> Optional[float]:
    """Safe parsing of km (handles , and .)."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def apply_midnight_correction(times: Sequence[float]) -> List[float]:
    """Correct a sequence of raw decimal-hour times for midnight crossings.

    Uses a cumulative day_offset counter: whenever time drops by >12 h
    compared to the previous *adjusted* value, assume a midnight crossing
    and add another 24 h.
    """
    result: List[float] = []
    day_offset = 0
    prev_adj: Optional[float] = None
    for t in times:
        adj = t + day_offset * 24
        if prev_adj is not None and (prev_adj - adj) > 12:
            day_offset += 1
            adj += 24
        result.append(adj)
        prev_adj = adj
    return result


def parse_time(value) -> Optional[float]:
    """
    Parse time to decimal hours.
    Supports:
    - Excel time as float (0.25 = 6:00)
    - text in "hh:mm"
    - text in "hh.mm" (two digits after dot = minutes)
    """
    # Handle NaN / missing
    try:
        if pd.isna(value):
            return None
    except Exception:
        # Some objects may raise in isna, ignore and continue
        pass

    # datetime-like (Timestamp / datetime / time)
    try:
        if hasattr(value, "hour"):
            h = int(value.hour)
            m = int(getattr(value, "minute", 0) or 0)
            s_sec = int(getattr(value, "second", 0) or 0)
            return h + m / 60 + s_sec / 3600
    except Exception:
        # fallthrough do parsowania tekstowego
        pass

    # Numeric value: Excel day fraction (0–1) or already in hours
    if isinstance(value, (int, float)):
        f = float(value)
        if f < 1:
            return f * 24  # Excel day fraction (e.g., 0.25 = 6:00)
        return f           # Already in hours (e.g., 6 = 6:00)

    s = str(value).strip()
    # Support suffix like "(+1)" meaning +1 day
    plus_days = 0
    m = re.search(r"\(\s*\+(\d+)\s*\)\s*$", s)
    if m:
        try:
            plus_days = int(m.group(1))
        except Exception:
            plus_days = 0
        s = s[: m.start()].strip()

    # Normalize decimal comma -> dot for hh.mm and float-like strings
    s_norm = s.replace(",", ".")

    # format hh:mm or hh:mm:ss
    if ":" in s_norm:
        try:
            parts = s_norm.split(":")
            h = int(parts[0]) if parts[0] != "" else 0
            m = int(parts[1]) if len(parts) > 1 and parts[1] != "" else 0
            sec = int(parts[2]) if len(parts) > 2 and parts[2] != "" else 0
            return h + m / 60 + sec / 3600 + 24 * plus_days
        except Exception:
            # not a valid hh:mm string
            return None

    # format hh.mm (two-digit minutes) OR textual Excel float like '0.25'
    if "." in s_norm:
        try:
            h_part, m_part = s_norm.split(".", 1)
            # If minutes part has exactly two digits, treat as hh.mm (minutes)
            if len(m_part) == 2 and m_part.isdigit() and h_part.lstrip("+-").isdigit():
                h_val = int(h_part)
                m_val = int(m_part)
                return h_val + m_val / 60 + 24 * plus_days
            # Distinguish Excel day fraction (< 1) from already-in-hours value
            f_val = float(s_norm)
            if f_val < 1:
                return f_val * 24 + 24 * plus_days  # Excel day fraction
            return f_val + 24 * plus_days  # Already in hours
        except Exception:
            return None

    # fallback: not recognized — try plain integer hours (e.g., "23"), then apply plus_days
    if s_norm.isdigit():
        try:
            return float(int(s_norm)) + 24 * plus_days
        except Exception:
            return None
    return None

def format_time_hhmm(t: float) -> str:
    """Convert decimal hours to bare 'HH:MM' (no day suffix)."""
    h = int(t) % 24
    m = int(round((t % 1) * 60))
    if m == 60:
        h = (h + 1) % 24
        m = 0
    return f"{h:02d}:{m:02d}"


def format_time_decimal(t: float) -> str:
    """Convert decimal hours to 'HH:MM' with optional +N days."""
    if t < 0:
        t = t % 24
    total_h = int(t)
    m = int(round((t % 1) * 60))
    if m == 60:
        total_h += 1
        m = 0
    days = total_h // 24
    h = total_h % 24
    if days == 0:
        return f"{h:02d}:{m:02d}"
    else:
        return f"{h:02d}:{m:02d} (+{days})"

# ===================== Header detection =====================

def find_headers(df: pd.DataFrame) -> Dict[str, Optional[int]]:
    """Find positions of key headers."""
    pos = dict(
        train_row=None,
        km_col=None,
        station_col=None,
        station_start_row=None,
        station_end_row=None,
    )
    rows, cols = df.shape

    # Accept common variants (normalized and without trailing colon)
    TRAIN_HEADER_VARIANTS = {
        "numer pociagu",
        "nr pociagu",
        "pociag",
        "train number",
    }
    KM_HEADER_VARIANTS = {
        "km",
        "kilometraz",
        "kilometr",
    }
    STATION_START_VARIANTS = {
        "ze stacji",
        "od stacji",
        "start stacji",
    }
    STATION_END_VARIANTS = {
        "do stacji",
        "na stacje",
        "cel stacji",
        "koniec stacji",
    }

    for r in range(rows):
        for c in range(cols):
            v = normalize(df.iat[r, c]).rstrip(":")
            if v in TRAIN_HEADER_VARIANTS and pos["train_row"] is None:
                pos["train_row"] = r
            elif v in KM_HEADER_VARIANTS and pos["km_col"] is None:
                pos["km_col"] = c
            elif v in STATION_START_VARIANTS and pos["station_start_row"] is None:
                pos["station_start_row"] = r
                if pos["station_col"] is None:
                    pos["station_col"] = c
            elif v in STATION_END_VARIANTS and pos["station_end_row"] is None:
                pos["station_end_row"] = r

    return pos

# ===================== Data extraction =====================

def extract_stations(
    df: pd.DataFrame,
    start_row: int,
    end_row: int,
    station_col: int,
    km_col: int,
) -> List[Tuple[float, str, int]]:
    """Return list of (km, station, row_idx) from given columns."""
    stations: List[Tuple[float, str, int]] = []
    start_r = start_row + 1
    end_r = end_row - 1
    end_r = max(end_r, start_r - 1)

    for r in range(start_r, end_r + 1):
        station_raw = df.iat[r, station_col] if station_col is not None else None
        km_raw = df.iat[r, km_col] if km_col is not None else None

        station_name = None if pd.isna(station_raw) else str(station_raw).strip()
        km = parse_km(km_raw)

        if station_name and (km is not None):
            stations.append((km, station_name, r))
    return stations

def extract_train_columns(
    df: pd.DataFrame,
    train_row: int,
    station_start_row: Optional[int] = None,
    station_end_row: Optional[int] = None,
) -> Dict[str, int]:
    """Return map {train_number_key: column_index}.

    Detection rules improved:
    - A header cell is considered a train number candidate if its string contains any digit.
    - If the header cell is part of a merged header spanning multiple columns (subsequent header cells are NaN),
      we inspect each column in that span: if at least one station row below has a parsable time (parse_time),
      that column is treated as a time column for this train number.
    - If header is not merged (single column), we treat that same column as the time column and verify it
      against station rows when available; otherwise fall back to previous c+1 behavior.

    When multiple columns map to the same train number, unique keys are created by appending
    ' (2)', ' (3)', ... so entries remain distinct.
    """
    if train_row is None:
        return {}

    mapping: Dict[str, int] = {}
    counters: Dict[str, int] = {}
    ncols = df.shape[1]

    # helper to create unique key when duplicates appear
    def unique_key(base: str) -> str:
        if base not in counters:
            counters[base] = 1
            return base
        else:
            counters[base] += 1
            return f"{base} ({counters[base]})"

    # determine station row search range (if provided)
    station_rows = None
    if station_start_row is not None and station_end_row is not None:
        start_r = station_start_row + 1
        end_r = max(station_end_row - 1, start_r - 1)
        if end_r >= start_r:
            station_rows = list(range(start_r, end_r + 1))

    c = 0
    while c < ncols:
        v = df.iat[train_row, c]
        if pd.isna(v):
            c += 1
            continue

        s_raw = str(v).strip()
        s_norm = normalize(s_raw)
        # candidate if contains any digit
        if any(ch.isdigit() for ch in s_raw):
            # detect span: originally-merged (NaN followers) OR contiguous identical headers after unmerge
            span_end = c
            while span_end + 1 < ncols:
                next_val = df.iat[train_row, span_end + 1]
                if pd.isna(next_val):
                    span_end += 1
                    continue
                next_norm = normalize(str(next_val).strip())
                if next_norm == s_norm and next_norm != "":
                    span_end += 1
                    continue
                break

            # columns that belong to this header span
            cols_in_span = list(range(c, span_end + 1))

            # function to check if column j contains any parsable time in station rows
            def column_has_time(j: int) -> bool:
                if station_rows is None:
                    return False
                for r in station_rows:
                    try:
                        val = df.iat[r, j]
                    except Exception:
                        continue
                    if pd.isna(val):
                        continue
                    if parse_time(val) is not None:
                        return True
                return False

            if len(cols_in_span) == 1:
                # non-merged header — assume times are in the same column; if verification possible, check it
                time_col = c
                if station_rows is not None and not column_has_time(time_col):
                    # fallback: perhaps times are in the next column as before
                    if c + 1 < ncols and column_has_time(c + 1):
                        time_col = c + 1
                    else:
                        # fallback to original heuristic c+1 (if in bounds)
                        time_col = c + 1 if c + 1 < ncols else c

                key = unique_key(s_raw)
                mapping[key] = time_col
            else:
                # merged header — inspect each column in the span and add those that contain times
                added_any = False
                for j in cols_in_span:
                    if column_has_time(j):
                        key = unique_key(s_raw)
                        mapping[key] = j
                        added_any = True

                # if none of the span columns had parsable times but we have no station_rows to check,
                # fall back to mapping the first column after header (c+1) as before
                if not added_any:
                    for j in cols_in_span:
                        time_col = j + 1 if j + 1 < ncols else j
                        key = unique_key(s_raw)
                        mapping[key] = time_col

            # jump to column after span
            c = span_end + 1
        else:
            c += 1

    return mapping

def extract_train_paths(
    df: pd.DataFrame,
    stations: List[Tuple[float, str, int]],
    train_columns: Dict[str, int],
    debug: bool = False,
) -> Dict[str, List[Tuple[float, float, str]]]:
    """
    Return {train_number: [(time_decimal, km, station_name), ...]}.
    Handles midnight crossing correctly.
    """
    paths: Dict[str, List[Tuple[float, float, str]]] = {}

    def dbg(msg: str) -> None:
        if debug:
            print(msg)

    for train_nr, col in train_columns.items():
        raw_entries: List[Tuple[float, float, str]] = []  # (raw_time, km, station)
        dbg(f"\nProcessing train {train_nr}")

        for km, station, r in stations:
            val = df.iat[r, col]
            t = parse_time(val)
            if t is not None:
                dbg(f"Station: {station}, Raw time: {val}, Parsed time: {t}")
                raw_entries.append((t, km, station))

        if raw_entries:
            raw_times = [e[0] for e in raw_entries]
            corrected_times = apply_midnight_correction(raw_times)
            points = [
                (corrected_times[i], raw_entries[i][1], raw_entries[i][2])
                for i in range(len(raw_entries))
            ]
            paths[train_nr] = points
    return paths

