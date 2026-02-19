import React from "react";
import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib";
import { AgGridReact } from "ag-grid-react";
import {
  ColDef,
  GridReadyEvent,
  CellValueChangedEvent,
  CellDoubleClickedEvent,
  CellClickedEvent,
  FirstDataRenderedEvent,
  GridApi,
} from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const SYSTEM_FIELDS = new Set(["km", "stacja", "_station_raw", "_stop_type"]);

type TrainGridArgs = {
  rowData: any[];
  columnDefs: ColDef[];
  height?: number;
  theme?: string;
  trainColors?: Record<string, string>;
  colorMode?: boolean;
};

class TrainGrid extends StreamlitComponentBase {
  private gridApi?: GridApi;

  public render = () => {
    const { rowData = [], columnDefs = [], height = 400, theme = "ag-theme-alpine",
            trainColors = {}, colorMode = false } =
      (this.props.args as TrainGridArgs) || {};

    // Apply background colors to train columns
    const processedColumnDefs = columnDefs.map((col: ColDef) => {
      const field = col.field || "";
      if (SYSTEM_FIELDS.has(field)) return col;
      const color = trainColors[field];
      if (color && color !== "#000000") {
        return {
          ...col,
          cellStyle: { backgroundColor: hexToRgba(color, 0.15) },
        };
      }
      return col;
    });

    const defaultColDef: ColDef = {
      editable: true,
      sortable: true,
      filter: true,
      resizable: true,
    };

    const onGridReady = (e: GridReadyEvent) => {
      this.gridApi = e.api;
      Streamlit.setFrameHeight(height + 24);
    };

    const onFirstDataRendered = (_e: FirstDataRenderedEvent) => {
      Streamlit.setFrameHeight(height + 24);
    };

    const onCellValueChanged = (e: CellValueChangedEvent) => {
      const payload = {
        type: "cellValueChanged" as const,
        rowIndex: e.node.rowIndex,
        field: e.colDef.field,
        oldValue: e.oldValue,
        newValue: e.newValue,
        row: e.data,
        _ts: Date.now(),
      };
      Streamlit.setComponentValue(payload);
    };

    const onCellDoubleClicked = colorMode ? undefined : (e: CellDoubleClickedEvent) => {
      const payload = {
        type: "cellDoubleClick" as const,
        rowIndex: e.node.rowIndex,
        field: e.colDef.field,
        row: e.data,
        _ts: Date.now(),
      };
      Streamlit.setComponentValue(payload);
    };

    const onCellClicked = colorMode ? (e: CellClickedEvent) => {
      const field = e.colDef.field || "";
      if (SYSTEM_FIELDS.has(field)) return;
      const payload = {
        type: "cellClick" as const,
        field,
        row: e.data,
        _ts: Date.now(),
      };
      Streamlit.setComponentValue(payload);
    } : undefined;

    return (
      <div className={theme} style={{ width: "100%", height, borderRadius: 8, overflow: "hidden" }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={processedColumnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          onFirstDataRendered={onFirstDataRendered}
          onCellValueChanged={onCellValueChanged}
          onCellDoubleClicked={onCellDoubleClicked}
          onCellClicked={onCellClicked}
        />
      </div>
    );
  };
}

export default withStreamlitConnection(TrainGrid);
