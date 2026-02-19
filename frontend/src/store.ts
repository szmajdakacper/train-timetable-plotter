import { create } from "zustand";
import type { TrainsData } from "./types";

interface AppState {
  // Data
  sheets: string[];
  selectedSheet: string;
  trainsData: TrainsData | null;
  trainColors: Record<string, string>;

  // UI
  activeColor: string | null;
  loading: boolean;
  error: string | null;
  plotHeight: number;

  // Actions
  setSheets: (sheets: string[], selected: string) => void;
  setTrainsData: (data: TrainsData) => void;
  setSelectedSheet: (sheet: string) => void;
  setTrainColors: (colors: Record<string, string>) => void;
  setActiveColor: (color: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPlotHeight: (height: number) => void;
}

export const useStore = create<AppState>((set) => ({
  sheets: [],
  selectedSheet: "",
  trainsData: null,
  trainColors: {},
  activeColor: null,
  loading: false,
  error: null,
  plotHeight: 600,

  setSheets: (sheets, selected) => set({ sheets, selectedSheet: selected }),
  setTrainsData: (data) =>
    set({
      trainsData: data,
      trainColors: data.train_colors,
      selectedSheet: data.selected_sheet,
    }),
  setSelectedSheet: (sheet) => set({ selectedSheet: sheet }),
  setTrainColors: (colors) => set({ trainColors: colors }),
  setActiveColor: (color) => set({ activeColor: color }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setPlotHeight: (height) => set({ plotHeight: height }),
}));
