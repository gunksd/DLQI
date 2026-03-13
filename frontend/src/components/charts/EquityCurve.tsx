"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { BLUE, GAIN_COLOR } from "./theme";

interface EquityCurveProps {
  data: { dates: string[]; strategy: number[]; benchmark: number[] };
  height?: number;
}

export function EquityCurve({ data, height = 350 }: EquityCurveProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: ["策略收益", "基准收益"],
        top: 5,
        textStyle: { color: "#9CA3AF", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: { left: 60, right: 20, top: 40, bottom: 30 },
      xAxis: {
        type: "category",
        data: data.dates,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#6B7280", fontSize: 10, formatter: "{value}" },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series: [
        {
          name: "策略收益",
          type: "line",
          data: data.strategy,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2, color: BLUE },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: BLUE + "30" },
              { offset: 1, color: BLUE + "00" },
            ]),
          },
        },
        {
          name: "基准收益",
          type: "line",
          data: data.benchmark,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, color: "#6B7280", type: "dashed" },
        },
      ],
      dataZoom: [{ type: "inside", start: 0, end: 100 }],
    }),
    [data.dates, data.strategy, data.benchmark],
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

export function generateMockEquityData(days = 365) {
  const dates: string[] = [],
    strategy: number[] = [],
    benchmark: number[] = [];
  let sv = 0,
    bv = 0;
  const base = new Date("2024-01-01");
  for (let i = 0; i < days; i++) {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
    sv += (Math.random() - 0.45) * 0.015;
    bv += (Math.random() - 0.48) * 0.012;
    strategy.push(sv);
    benchmark.push(bv);
  }
  return { dates, strategy, benchmark };
}
