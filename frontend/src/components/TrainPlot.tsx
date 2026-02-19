import React, { useRef, useCallback, useMemo } from "react";
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
import type { StationItem, PlotSeries } from "../types";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent,
  CanvasRenderer,
]);

interface Props {
  yStations: StationItem[];
  series: PlotSeries[];
  xMinMs: number;
  xMaxMs: number;
  height: number;
  trainColors: Record<string, string>;
  colorMode: boolean;
  onPointClick?: (train: string) => void;
  onPointDoubleClick?: (info: {
    train: string;
    ms: number;
    km: number;
    station: string;
    sheet: string;
  }) => void;
}

function fmtTime(msInDay: number): string {
  const dayMs = 24 * 60 * 60 * 1000;
  const ms = ((Number(msInDay) % dayMs) + dayMs) % dayMs;
  const totalMin = Math.floor(ms / 60000);
  const hh = String(Math.floor(totalMin / 60)).padStart(2, "0");
  const mm = String(totalMin % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

export default function TrainPlot({
  yStations,
  series,
  xMinMs,
  xMaxMs,
  height,
  trainColors,
  colorMode,
  onPointClick,
  onPointDoubleClick,
}: Props) {
  const echartsRef = useRef<any>(null);

  const kmValues = useMemo(
    () => yStations.map((s) => s.km),
    [yStations],
  );
  const yMin = kmValues.length ? Math.min(...kmValues) : undefined;
  const yMax = kmValues.length ? Math.max(...kmValues) : undefined;

  const echartsSeries = useMemo(() => {
    return series.map((s) => {
      const trainNum = s.name.replace(/ \([^)]+\)$/, "");
      const color = trainColors[trainNum] || "#000";
      return {
        name: s.name,
        type: "line" as const,
        showSymbol: true,
        symbolSize: 5,
        smooth: false,
        data: s.points,
        lineStyle: { color, width: 1.5 },
        itemStyle: { color },
        tooltip: { trigger: "item" },
      };
    });
  }, [series, trainColors]);

  const option = useMemo(() => {
    const opt: any = {
      backgroundColor: "#f7f2e8",
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
            let station = "";
            if (yStations.length > 0) {
              let best = yStations[0];
              let bestDiff = Math.abs(yStations[0].km - km);
              for (let i = 1; i < yStations.length; i++) {
                const diff = Math.abs(yStations[i].km - km);
                if (diff < bestDiff) {
                  best = yStations[i];
                  bestDiff = diff;
                }
              }
              station = best.name;
            }
            return `nr poc: ${train}<br/>stacja: ${station}<br/>km: ${Number(km).toFixed(3)}<br/>godzina: ${hhmm}`;
          } catch {
            return "";
          }
        },
      },
      xAxis: {
        type: "time",
        min: xMinMs,
        max: xMaxMs,
        axisLabel: { formatter: (val: number) => fmtTime(val) },
        splitLine: {
          show: true,
          lineStyle: { color: "#999", width: 1, type: "solid" },
        },
        minorSplitLine: { show: true },
        minorTick: { show: true, splitNumber: 2 },
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
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "none" },
        {
          type: "slider",
          xAxisIndex: 0,
          height: 30,
          bottom: 25,
          startValue: xMinMs,
          endValue: xMaxMs,
          labelFormatter: (value: any) => fmtTime(value),
          filterMode: "none",
        },
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

    // Station mark lines on first series
    if (opt.series.length > 0 && yStations.length > 0) {
      const markLines = yStations.map((s) => ({
        yAxis: s.km,
        label: {
          formatter: s.name,
          position: "insideStart",
          align: "left",
          distance: 6,
        },
        lineStyle: { type: "dashed", color: "#bbb" },
      }));
      opt.series[0].markLine = { silent: true, data: markLines };
    }

    return opt;
  }, [echartsSeries, xMinMs, xMaxMs, yMin, yMax, yStations]);

  const onEvents = useMemo(() => {
    const events: Record<string, (p: any) => void> = {};

    if (colorMode) {
      events.click = (p: any) => {
        if (!p || p.componentType !== "series") return;
        const raw = p.data;
        const train =
          raw?.train ?? p.seriesName?.replace(/ \([^)]+\)$/, "") ?? "";
        onPointClick?.(train);
      };
    } else {
      events.dblclick = (p: any) => {
        if (!p || p.componentType !== "series") return;
        const raw = p.data;
        const arr = Array.isArray(raw?.value)
          ? raw.value
          : Array.isArray(raw)
            ? raw
            : p.value;
        if (!Array.isArray(arr)) return;
        const ms = arr[0];
        const km = arr[1];
        const train = raw?.train ?? p.seriesName ?? "";
        const sheet = raw?.sheet ?? "";
        let station = raw?.station ?? "";
        if (!station && yStations.length > 0) {
          let best = yStations[0];
          let bestDiff = Math.abs(yStations[0].km - km);
          for (let i = 1; i < yStations.length; i++) {
            const diff = Math.abs(yStations[i].km - km);
            if (diff < bestDiff) {
              best = yStations[i];
              bestDiff = diff;
            }
          }
          station = best.name;
        }
        onPointDoubleClick?.({ train, ms, km, station, sheet });
      };
    }
    return events;
  }, [colorMode, onPointClick, onPointDoubleClick, yStations]);

  return (
    <div
      style={{
        width: "100%",
        height,
        background: "#f7f2e8",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <ReactEChartsCore
        ref={echartsRef}
        echarts={echarts}
        option={option}
        style={{ width: "100%", height: "100%" }}
        onEvents={onEvents}
      />
    </div>
  );
}
