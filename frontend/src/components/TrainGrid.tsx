import React, { useMemo, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import type {
  ColDef,
  CellDoubleClickedEvent,
  CellClickedEvent,
} from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Compute a font-size (px) that fits `text` inside `colWidth` px. */
function headerFontSize(text: string, colWidth: number): number {
  const maxFontPx = 13;
  const minFontPx = 8;
  const charWidthRatio = 0.62; // approx char width / font-size for sans-serif
  const padding = 16; // left+right padding in AG Grid header cell
  const available = colWidth - padding;
  const needed = text.length * charWidthRatio * maxFontPx;
  if (needed <= available) return maxFontPx;
  const scaled = available / (text.length * charWidthRatio);
  return Math.max(minFontPx, Math.round(scaled * 10) / 10);
}

function AutofitHeader(props: any) {
  const text = props.displayName || "";
  const colWidth = props.column?.getActualWidth?.() || 80;
  const fontSize = headerFontSize(text, colWidth);
  return (
    <span
      style={{ fontSize, whiteSpace: "nowrap", overflow: "hidden" }}
      title={text}
    >
      {text}
    </span>
  );
}

const SYSTEM_FIELDS = new Set(["km", "stacja", "_station_raw", "_stop_type", "_decimals"]);

interface Props {
  rowData: Record<string, any>[];
  columnDefs: ColDef[];
  height: number;
  trainColors: Record<string, string>;
  colorMode: boolean;
  onCellDoubleClick?: (info: {
    field: string;
    row: Record<string, any>;
  }) => void;
  onCellClick?: (field: string) => void;
}

export default function TrainGrid({
  rowData,
  columnDefs,
  height,
  trainColors,
  colorMode,
  onCellDoubleClick,
  onCellClick,
}: Props) {
  // Stable key that changes when the set of colored trains changes,
  // forcing AG Grid to re-mount and apply fresh cellStyle values.
  const gridKey = useMemo(() => {
    const entries = Object.entries(trainColors)
      .filter(([, v]) => v && v !== "#000000")
      .sort(([a], [b]) => a.localeCompare(b));
    return entries.map(([k, v]) => `${k}:${v}`).join("|");
  }, [trainColors]);

  const processedColumnDefs = useMemo(() => {
    return columnDefs.map((col) => {
      const field = col.field || "";
      if (SYSTEM_FIELDS.has(field)) return col;
      const color = trainColors[field];
      const cellStyle =
        color && color !== "#000000"
          ? { backgroundColor: hexToRgba(color, 0.15) }
          : undefined;
      return {
        ...col,
        cellStyle,
        editable: colorMode ? false : col.editable,
        headerComponent: AutofitHeader,
      };
    });
  }, [columnDefs, trainColors, colorMode]);

  const defaultColDef: ColDef = useMemo(
    () => ({
      sortable: false,
      filter: false,
      resizable: true,
    }),
    [],
  );

  const onCellDoubleClicked = useCallback(
    (e: CellDoubleClickedEvent) => {
      if (colorMode) return;
      const field = e.colDef.field || "";
      if (SYSTEM_FIELDS.has(field)) return;
      onCellDoubleClick?.({ field, row: e.data });
    },
    [colorMode, onCellDoubleClick],
  );

  const onCellClicked = useCallback(
    (e: CellClickedEvent) => {
      if (!colorMode) return;
      const field = e.colDef.field || "";
      if (SYSTEM_FIELDS.has(field)) return;
      onCellClick?.(field);
    },
    [colorMode, onCellClick],
  );

  return (
    <div
      className="ag-theme-alpine"
      style={{ width: "100%", height, borderRadius: 8, overflow: "hidden" }}
    >
      <AgGridReact
        key={gridKey}
        rowData={rowData}
        columnDefs={processedColumnDefs}
        defaultColDef={defaultColDef}
        onCellDoubleClicked={onCellDoubleClicked}
        onCellClicked={onCellClicked}
      />
    </div>
  );
}
