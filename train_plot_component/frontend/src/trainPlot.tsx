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

  public componentDidMount(): void {
    Streamlit.setFrameHeight(this.getFrameHeight());
  }

  public componentDidUpdate(prevProps: Readonly<any>): void {
    const prevHeight = ((prevProps?.args as TrainPlotArgs) || {}).height ?? 420;
    const currHeight = ((this.props.args as TrainPlotArgs) || {}).height ?? 420;
    if (prevHeight !== currHeight) {
      Streamlit.setFrameHeight(this.getFrameHeight());
    }
  }
  public render = () => {
    const { yStations = [], series = [], xMinMs, xMaxMs, height = 420 } = (this.props.args as TrainPlotArgs) || {};

    const echartsSeries = series.map(s => ({
      name: s.name,
      type: "line" as const,
      showSymbol: true,
      symbolSize: 5,
      smooth: false,
      data: s.points,
      lineStyle: { color: "#000", width: 1.5 },
      itemStyle: { color: "#000" },
      tooltip: { trigger: "item" },
    }));

    const option = {
      grid: { left: 80, right: 24, top: 24, bottom: 40 },
      color: ["#000"],
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
            const date = new Date(ms);
            const hh = String(date.getUTCHours()).padStart(2, "0");
            const mm = String(date.getUTCMinutes()).padStart(2, "0");
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
            return `nr poc: ${train}<br/>stacja: ${station}<br/>km: ${Number(km).toFixed(3)}<br/>godzina: ${hh}:${mm}`;
          } catch {
            return "";
          }
        }
      },
      xAxis: {
        type: "time",
        min: xMinMs ?? undefined,
        max: xMaxMs ?? undefined,
        axisLabel: { formatter: (val: number) => new Date(val).toTimeString().slice(0,5) },
        splitLine: { show: true, lineStyle: { color: "#999", width: 1, type: "solid" } },
        minorSplitLine: { show: true },
        minorTick: { show: true, splitNumber: 2 }, // 30 min i 15 min przez minor grid
      },
      yAxis: {
        type: "value",
        inverse: false,
        name: "km",
        axisLabel: { formatter: (v: number) => v.toFixed(3) },
        splitLine: { show: true },
        axisPointer: { show: false },
      },
      // Dorysujemy markery stacji jako markLine na osi Y
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "slider", xAxisIndex: 0 },
      ],
      series: echartsSeries,
    };

    // Dodaj poziome linie stacji (markLine) do pierwszej serii, jeśli istnieje
    if (option.series && option.series.length > 0 && Array.isArray(yStations) && yStations.length > 0) {
      const markLines = yStations.map(s => ({
        yAxis: s.km,
        label: { formatter: s.name, position: "start" },
        lineStyle: { type: "dashed", color: "#bbb" },
      }));
      (option.series[0] as any).markLine = { silent: true, data: markLines };
    }

    // wysokość ustawiana w lifecycle; brak wywołań w renderze

    return (
      <div style={{ width: "100%", height }}>
        <ReactEChartsCore echarts={echarts} option={option} style={{ width: "100%", height: "100%" }} />
      </div>
    );
  };
}

export default withStreamlitConnection(TrainPlot);


