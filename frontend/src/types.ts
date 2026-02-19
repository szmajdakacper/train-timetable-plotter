export interface StationItem {
  name: string;
  km: number;
}

export interface PlotPoint {
  value: [number, number]; // [ms, km]
  station: string;
  train: string;
  sheet: string;
  stopType: string | null;
}

export interface PlotSeries {
  name: string;
  points: PlotPoint[];
}

export interface ColumnDef {
  field: string;
  headerName: string;
  editable: boolean;
  width: number;
}

export interface GridRow {
  km: string;
  stacja: string;
  _station_raw: string;
  _stop_type: string | null;
  _decimals: Record<string, number>;
  [trainNumber: string]: any;
}

export interface TrainsData {
  grid_rows: GridRow[];
  column_defs: ColumnDef[];
  plot_series: PlotSeries[];
  station_items: StationItem[];
  x_min_ms: number;
  x_max_ms: number;
  train_colors: Record<string, string>;
  selected_sheet: string;
}

export interface SheetsData {
  sheets: string[];
  selected_sheet: string;
}

export interface UploadResponse {
  ok: boolean;
  sheets: string[];
  selected_sheet: string;
  message: string;
}
