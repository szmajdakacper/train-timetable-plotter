import React, { useCallback, useState } from "react";
import { useStore } from "./store";
import * as api from "./api";
import FileUpload from "./components/FileUpload";
import SheetSelector from "./components/SheetSelector";
import TrainPlot from "./components/TrainPlot";
import TrainGrid from "./components/TrainGrid";
import ColorToolbar from "./components/ColorToolbar";
import EditDialog from "./components/EditDialog";
import ExportBar from "./components/ExportBar";
import XlsxRequirements from "./components/XlsxRequirements";
import "./styles/theme.css";

interface EditInfo {
  station: string;
  km: number;
  trainNumber: string;
  sheet: string;
  defaultHour: number;
  defaultMinute: number;
  stopType: string | null;
  hasExistingTime: boolean;
  dayOffset: number;
}

export default function App() {
  const {
    sheets,
    selectedSheet,
    trainsData,
    trainColors,
    activeColor,
    loading,
    error,
    plotHeight,
    setSheets,
    setTrainsData,
    setTrainColors,
    setActiveColor,
    setLoading,
    setError,
    setPlotHeight,
  } = useStore();

  const [editInfo, setEditInfo] = useState<EditInfo | null>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.uploadFile(file);
        setSheets(res.sheets, res.selected_sheet);
        const trains = await api.getTrains();
        setTrainsData(trains);
      } catch (e: any) {
        setError(e.message || "Błąd wczytywania pliku");
      } finally {
        setLoading(false);
      }
    },
    [setSheets, setTrainsData, setLoading, setError],
  );

  const handleSheetSelect = useCallback(
    async (sheet: string) => {
      setLoading(true);
      try {
        await api.selectSheet(sheet);
        const trains = await api.getTrains();
        setTrainsData(trains);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [setTrainsData, setLoading, setError],
  );

  const handleColorSelect = useCallback(
    (color: string) => setActiveColor(color),
    [setActiveColor],
  );

  const handleColorDone = useCallback(
    () => setActiveColor(null),
    [setActiveColor],
  );

  const handleClearAllColors = useCallback(async () => {
    try {
      const colors = await api.clearAllColors();
      setTrainColors(colors);
      setActiveColor(null);
    } catch (e: any) {
      setError(e.message);
    }
  }, [setTrainColors, setActiveColor, setError]);

  const handlePointClick = useCallback(
    async (train: string) => {
      if (activeColor === null) return;
      try {
        const colors = await api.setColor(train, activeColor);
        setTrainColors(colors);
      } catch (e: any) {
        setError(e.message);
      }
    },
    [activeColor, setTrainColors, setError],
  );

  const handleCellClick = useCallback(
    async (field: string) => {
      if (activeColor === null) return;
      try {
        const colors = await api.setColor(field, activeColor);
        setTrainColors(colors);
      } catch (e: any) {
        setError(e.message);
      }
    },
    [activeColor, setTrainColors, setError],
  );

  const handlePointDoubleClick = useCallback(
    (info: { train: string; ms: number; km: number; station: string; sheet: string }) => {
      if (activeColor !== null) return;
      const totalHours = info.ms / 3_600_000;
      const h = Math.floor(totalHours) % 24;
      const m = Math.floor((totalHours % 1) * 60);
      const dayOffset = Math.floor(totalHours / 24);

      // Try to find stop_type from grid data
      let stopType: string | null = null;
      if (trainsData) {
        for (const row of trainsData.grid_rows) {
          if (
            row._station_raw === info.station &&
            Math.abs(parseFloat(row.km) - info.km) < 0.01
          ) {
            const timeVal = row[info.train];
            if (timeVal) {
              stopType = row._stop_type;
              break;
            }
          }
        }
      }

      setEditInfo({
        station: info.station,
        km: info.km,
        trainNumber: info.train,
        sheet: info.sheet || selectedSheet,
        defaultHour: h,
        defaultMinute: m,
        stopType,
        hasExistingTime: true,
        dayOffset,
      });
    },
    [activeColor, selectedSheet, trainsData],
  );

  const handleCellDoubleClick = useCallback(
    (info: { field: string; row: Record<string, any> }) => {
      if (activeColor !== null) return;
      const station = String(info.row._station_raw || info.row.stacja || "");
      const stopType = info.row._stop_type || null;
      const km = parseFloat(String(info.row.km || "0").replace(",", "."));
      const currentTimeStr = info.row[info.field] || "";

      let h = 0,
        m = 0,
        hasExisting = false,
        dayOffset = 0;
      if (currentTimeStr) {
        const parts = currentTimeStr.split(":");
        h = parseInt(parts[0]) || 0;
        m = parseInt(parts[1]) || 0;
        hasExisting = true;
      }

      setEditInfo({
        station,
        km,
        trainNumber: info.field,
        sheet: selectedSheet,
        defaultHour: h,
        defaultMinute: m,
        stopType,
        hasExistingTime: hasExisting,
        dayOffset,
      });
    },
    [activeColor, selectedSheet],
  );

  const handleSave = useCallback(
    async (hour: number, minute: number, propagate: boolean) => {
      if (!editInfo) return;
      setLoading(true);
      try {
        const data = await api.saveTime({
          sheet: editInfo.sheet,
          station: editInfo.station,
          km: editInfo.km,
          train_number: editInfo.trainNumber,
          hour,
          minute,
          day_offset: editInfo.dayOffset,
          stop_type: editInfo.stopType,
          propagate,
        });
        setTrainsData(data);
        setEditInfo(null);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [editInfo, setTrainsData, setLoading, setError],
  );

  const handleClear = useCallback(async () => {
    if (!editInfo) return;
    setLoading(true);
    try {
      const data = await api.clearTime({
        sheet: editInfo.sheet,
        station: editInfo.station,
        km: editInfo.km,
        train_number: editInfo.trainNumber,
        stop_type: editInfo.stopType,
      });
      setTrainsData(data);
      setEditInfo(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [editInfo, setTrainsData, setLoading, setError]);

  const hasData = trainsData !== null && trainsData.grid_rows.length > 0;

  return (
    <div className="app">
      <h1>Rozkład Jazdy - wykresy z tabeli</h1>

      <FileUpload onUpload={handleUpload} loading={loading} />

      <XlsxRequirements />

      {error && <div className="error-msg">{error}</div>}

      {hasData && (
        <>
          <SheetSelector
            sheets={sheets}
            selected={selectedSheet}
            onSelect={handleSheetSelect}
          />

          <ExportBar />

          <ColorToolbar
            activeColor={activeColor}
            onSelectColor={handleColorSelect}
            onDone={handleColorDone}
            onClearAll={handleClearAllColors}
          />

          <section>
            <h2>Wykres tras pociągów</h2>
            <div className="plot-height-control">
              <label>Wysokość wykresu: {plotHeight}px</label>
              <input
                type="range"
                min={400}
                max={4000}
                step={100}
                value={plotHeight}
                onChange={(e) => setPlotHeight(parseInt(e.target.value))}
              />
            </div>
            <TrainPlot
              yStations={trainsData!.station_items}
              series={trainsData!.plot_series}
              xMinMs={trainsData!.x_min_ms}
              xMaxMs={trainsData!.x_max_ms}
              height={plotHeight}
              trainColors={trainColors}
              colorMode={activeColor !== null}
              onPointClick={handlePointClick}
              onPointDoubleClick={handlePointDoubleClick}
            />
          </section>

          <section>
            <h2>Tabela: km – stacja – pociągi</h2>
            <p className="sheet-caption">Arkusz: {selectedSheet}</p>
            <TrainGrid
              rowData={trainsData!.grid_rows}
              columnDefs={trainsData!.column_defs}
              height={Math.min(600, 100 + 26 * (trainsData!.grid_rows.length + 1))}
              trainColors={trainColors}
              colorMode={activeColor !== null}
              onCellDoubleClick={handleCellDoubleClick}
              onCellClick={handleCellClick}
            />
          </section>
        </>
      )}

      {!hasData && !loading && sheets.length === 0 && (
        <p className="empty-state">Brak danych do zbudowania tabeli. Wczytaj plik.</p>
      )}

      {editInfo && (
        <EditDialog
          station={editInfo.station}
          km={editInfo.km}
          trainNumber={editInfo.trainNumber}
          sheet={editInfo.sheet}
          defaultHour={editInfo.defaultHour}
          defaultMinute={editInfo.defaultMinute}
          stopType={editInfo.stopType}
          hasExistingTime={editInfo.hasExistingTime}
          onSave={handleSave}
          onClear={handleClear}
          onCancel={() => setEditInfo(null)}
        />
      )}

      <footer className="app-footer">
        &copy; {new Date().getFullYear()} Kacper Szmajda
      </footer>
    </div>
  );
}
