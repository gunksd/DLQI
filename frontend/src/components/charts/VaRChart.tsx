"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { CYAN, PURPLE, GAIN_COLOR, LOSS_COLOR } from "./theme";

interface VaRChartProps {
  data: {
    dates: string[];
    var95: number[];
    var99: number[];
    actualLoss: number[];
  };
  height?: number;
}

export function VaRChart({ data, height = 300 }: VaRChartProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: ["VaR (95%)", "VaR (99%)", "实际损失"],
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
        max: 0,
        axisLabel: { color: "#6B7280", fontSize: 10, formatter: "{value}" },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series: [
        {
          name: "VaR (95%)",
          type: "line",
          data: data.var95,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: CYAN },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: CYAN + "00" },
              { offset: 1, color: CYAN + "30" },
            ]),
          },
        },
        {
          name: "VaR (99%)",
          type: "line",
          data: data.var99,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: PURPLE },
        },
        {
          name: "实际损失",
          type: "scatter",
          symbolSize: 6,
          data: data.actualLoss.map((loss, i) => ({
            value: loss,
            itemStyle: {
              color: loss < data.var99[i] ? LOSS_COLOR : GAIN_COLOR,
            },
          })),
        },
      ],
    }),
    [data.dates, data.var95, data.var99, data.actualLoss],
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

export function generateMockVaRData(days = 60) {
  const dates: string[] = [],
    var95: number[] = [],
    var99: number[] = [],
    actualLoss: number[] = [];
  const base = new Date("2024-11-01");
  for (let i = 0; i < days; i++) {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
    const bv = -0.02 + Math.sin(i / 10) * 0.005 + (Math.random() - 0.5) * 0.005;
    var95.push(bv);
    var99.push(bv * 1.5);
    actualLoss.push(Math.min(0, (Math.random() - 0.6) * 0.03));
  }
  return { dates, var95, var99, actualLoss };
}
