import React from "react";
import { Streamlit, StreamlitComponentBase, withStreamlitConnection } from "streamlit-component-lib";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, CanvasRenderer]);

type TrainPlotArgs = {
  yStations: { name: string; km: number }[];
  series: { name: string; points: [number, number][] }[]; // [ms, km]
  xMinMs?: number | null;
  xMaxMs?: number | null;
  height?: number;
};

class TrainPlot extends StreamlitComponentBase {
  private getFrameHeight = (): number => {
    const { height = 420 } = (this.props.args as TrainPlotArgs) || {};
    return height + 24;
  };
  private lastHeight?: number;

  public componentDidMount(): void {
    this.lastHeight = this.getFrameHeight();
    Streamlit.setFrameHeight(this.lastHeight);
  }

  public componentDidUpdate(): void {
    const h = this.getFrameHeight();
    if (this.lastHeight !== h) {
      this.lastHeight = h;
      Streamlit.setFrameHeight(h);
    }
  }
  public render = () => {
    const { yStations = [], series = [], xMinMs, xMaxMs, height = 420 } = (this.props.args as TrainPlotArgs) || {};

    const fmtTime = (msInDay: number): string => {
      const dayMs = 24 * 60 * 60 * 1000;
      const ms = ((Number(msInDay) % dayMs) + dayMs) % dayMs; // keep within 0..dayMs
      const totalMin = Math.floor(ms / 60000);
      const hh = String(Math.floor(totalMin / 60)).padStart(2, "0");
      const mm = String(totalMin % 60).padStart(2, "0");
      return `${hh}:${mm}`;
    };

    const echartsSeries = series.map(s => ({
      name: s.name,
      type: "line" as const,
      showSymbol: true,
      symbolSize: 5,
      smooth: false,
      // Każdy punkt może być tablicą [ms, km] lub obiektem { value:[ms, km], station, sheet, train }
      data: s.points,
      lineStyle: { color: "#000", width: 1.5 },
      itemStyle: { color: "#000" },
      tooltip: { trigger: "item" },
    }));

    const kmValues = Array.isArray(yStations) && yStations.length > 0 ? yStations.map(s => (s as any).km as number) : [];
    const yMin = kmValues.length ? Math.min(...kmValues) : undefined;
    const yMax = kmValues.length ? Math.max(...kmValues) : undefined;

    const option = {
      grid: { left: 80, right: 60, top: 24, bottom: 80 },
      color: ["#000"],
      useUTC: true,
      tooltip: {
        trigger: "item",
        triggerOn: "mousemove|click",
        alwaysShowContent: false,
        appendToBody: true,
        formatter: (p: any) => {
          try {
            const train = p.seriesName || "";
            const ms = Array.isArray(p.value) ? p.value[0] : p.value?.x;
            const km = Array.isArray(p.value) ? p.value[1] : p.value?.y;
            const hhmm = fmtTime(ms);
            // znajdź najbliższą stację względem km
            let station = "";
            if (Array.isArray(yStations) && yStations.length > 0) {
              let best = yStations[0];
              let bestDiff = Math.abs((yStations[0] as any).km - km);
              for (let i = 1; i < yStations.length; i++) {
                const diff = Math.abs((yStations[i] as any).km - km);
                if (diff < bestDiff) { best = yStations[i] as any; bestDiff = diff; }
              }
              station = `${(best as any).name}`;
            }
            return `nr poc: ${train}<br/>stacja: ${station}<br/>km: ${Number(km).toFixed(3)}<br/>godzina: ${hhmm}`;
          } catch {
            return "";
          }
        }
      },
      xAxis: {
        type: "time",
        min: xMinMs ?? undefined,
        max: xMaxMs ?? undefined,
        axisLabel: { formatter: (val: number) => fmtTime(val) },
        splitLine: { show: true, lineStyle: { color: "#999", width: 1, type: "solid" } },
        minorSplitLine: { show: true },
        minorTick: { show: true, splitNumber: 2 }, // 30 min i 15 min przez minor grid
      },
      yAxis: {
        type: "value",
        inverse: false,
        name: "km",
        position: "left",
        axisLabel: { formatter: (v: number) => v.toFixed(3) },
        splitLine: { show: true },
        axisPointer: { show: false },
      },
      // Dorysujemy markery stacji jako markLine na osi Y
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "none" },
        {
          type: "slider",
          xAxisIndex: 0,
          height: 30,
          bottom: 25,
          startValue: xMinMs ?? undefined,
          endValue: xMaxMs ?? undefined,
          labelFormatter: (value: any) => fmtTime(value),
          filterMode: "none",
        },
        // Y-axis zoom (inside + slider)
        { type: "inside", yAxisIndex: 0, filterMode: "none" },
        {
          type: "slider",
          yAxisIndex: 0,
          orient: "vertical",
          right: 10,
          top: 24,
          bottom: 90,
          startValue: yMin,
          endValue: yMax,
          labelFormatter: (v: any) => {
            const n = typeof v === "number" ? v : Number(v);
            return isFinite(n) ? n.toFixed(3) : "";
          },
          filterMode: "none",
        },
      ],
      series: echartsSeries,
    };

    // Dodaj poziome linie stacji (markLine) do pierwszej serii, jeśli istnieje
    if (option.series && option.series.length > 0 && Array.isArray(yStations) && yStations.length > 0) {
      const markLines = yStations.map(s => ({
        yAxis: s.km,
        label: { formatter: s.name, position: "insideStart", align: "left", distance: 6 },
        lineStyle: { type: "dashed", color: "#bbb" },
      }));
      (option.series[0] as any).markLine = { silent: true, data: markLines };
    }

    // wysokość ustawiana w lifecycle; brak wywołań w renderze

    const onEvents = {
      dblclick: (p: any) => {
        try {
          if (!p || p.componentType !== "series") return;
          const raw = p.data;
          const arr = Array.isArray(raw?.value) ? raw.value : (Array.isArray(raw) ? raw : p.value);
          if (!Array.isArray(arr)) return;
          const ms = arr[0];
          const km = arr[1];
          const train = (raw?.train ?? p.seriesName) || "";
          const sheet = raw?.sheet;
          const station = raw?.station;
          // nearest station by km (fallback)
          let stationName = station;
          if (!stationName && Array.isArray(yStations) && yStations.length > 0) {
            let best = yStations[0];
            let bestDiff = Math.abs((yStations[0] as any).km - km);
            for (let i = 1; i < yStations.length; i++) {
              const diff = Math.abs((yStations[i] as any).km - km);
              if (diff < bestDiff) { best = yStations[i] as any; bestDiff = diff; }
            }
            stationName = `${(best as any).name}`;
          }
          Streamlit.setComponentValue({
            type: "pointDoubleClick",
            train,
            ms,
            km,
            station: stationName,
            sheet,
          });
        } catch { /* noop */ }
      }
    } as any;

    return (
      <div style={{ width: "100%", height }}>
        <ReactEChartsCore echarts={echarts} option={option} style={{ width: "100%", height: "100%" }} onEvents={onEvents} />
      </div>
    );
  };
}

export default withStreamlitConnection(TrainPlot);


