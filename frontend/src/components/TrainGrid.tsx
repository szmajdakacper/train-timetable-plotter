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
  const processedColumnDefs = useMemo(() => {
    return columnDefs.map((col) => {
      const field = col.field || "";
      if (SYSTEM_FIELDS.has(field)) return col;
      const color = trainColors[field];
      const cellStyle =
        color && color !== "#000000"
          ? { backgroundColor: hexToRgba(color, 0.15) }
          : undefined;
      return { ...col, cellStyle };
    });
  }, [columnDefs, trainColors]);

  const defaultColDef: ColDef = useMemo(
    () => ({
      sortable: true,
      filter: true,
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
        rowData={rowData}
        columnDefs={processedColumnDefs}
        defaultColDef={defaultColDef}
        onCellDoubleClicked={onCellDoubleClicked}
        onCellClicked={onCellClicked}
      />
    </div>
  );
}
