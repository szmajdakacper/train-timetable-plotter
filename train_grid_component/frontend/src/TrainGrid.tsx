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
  FirstDataRenderedEvent,
  GridApi,
} from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

type TrainGridArgs = {
  rowData: any[];
  columnDefs: ColDef[];
  height?: number;
  theme?: string;
};

class TrainGrid extends StreamlitComponentBase {
  private gridApi?: GridApi;

  public render = () => {
    const { rowData = [], columnDefs = [], height = 400, theme = "ag-theme-alpine" } =
      (this.props.args as TrainGridArgs) || {};

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
      };
      Streamlit.setComponentValue(payload);
    };

    const onCellDoubleClicked = (e: CellDoubleClickedEvent) => {
      const payload = {
        type: "cellDoubleClick" as const,
        rowIndex: e.node.rowIndex,
        field: e.colDef.field,
        row: e.data,
      };
      Streamlit.setComponentValue(payload);
    };

    return (
      <div className={theme} style={{ width: "100%", height, borderRadius: 8, overflow: "hidden" }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          onFirstDataRendered={onFirstDataRendered}
          onCellValueChanged={onCellValueChanged}
          onCellDoubleClicked={onCellDoubleClicked}
        />
      </div>
    );
  };
}

export default withStreamlitConnection(TrainGrid);


