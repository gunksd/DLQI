"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { LOSS_COLOR } from "./theme";

interface DrawdownChartProps {
  data: { dates: string[]; drawdown: number[] };
  height?: number;
}

export function DrawdownChart({ data, height = 250 }: DrawdownChartProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: { left: 60, right: 20, top: 15, bottom: 30 },
      xAxis: {
        type: "category",
        data: data.dates,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        max: 0,
        axisLabel: { color: "#6B7280", fontSize: 10, formatter: "{value}" },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series: [
        {
          type: "line",
          data: data.drawdown,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: LOSS_COLOR },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: LOSS_COLOR + "00" },
              { offset: 1, color: LOSS_COLOR + "40" },
            ]),
          },
        },
      ],
    }),
    [data.dates, data.drawdown],
  );

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}

export function generateMockDrawdownData(days = 365) {
  const dates: string[] = [],
    drawdown: number[] = [];
  let peak = 1,
    current = 1;
  const base = new Date("2024-01-01");
  for (let i = 0; i < days; i++) {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
    current *= 1 + (Math.random() - 0.48) * 0.02;
    peak = Math.max(peak, current);
    drawdown.push((current - peak) / peak);
  }
  return { dates, drawdown };
}
