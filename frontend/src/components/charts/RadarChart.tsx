"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { BLUE, PURPLE, AMBER, GAIN_COLOR } from "./theme";

interface RadarChartProps {
  data: {
    indicators: { name: string; max: number }[];
    models: { name: string; values: number[]; color: string }[];
  };
  height?: number;
}

export function RadarChart({ data, height = 350 }: RadarChartProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: data.models.map((m) => m.name),
        top: 5,
        textStyle: { color: "#9CA3AF", fontSize: 11 },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      radar: {
        indicator: data.indicators,
        shape: "polygon" as const,
        splitNumber: 5,
        axisName: { color: "#9CA3AF", fontSize: 11 },
        splitLine: { lineStyle: { color: "#1F2937" } },
        splitArea: {
          show: true,
          areaStyle: { color: ["#11182780", "#11182740"] },
        },
        axisLine: { lineStyle: { color: "#1F2937" } },
      },
      series: [
        {
          type: "radar",
          data: data.models.map((m) => ({
            name: m.name,
            value: m.values,
            lineStyle: { width: 2, color: m.color },
            areaStyle: { color: m.color + "33" },
            itemStyle: { color: m.color },
          })),
        },
      ],
    }),
    [data.indicators, data.models],
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

export function generateMockRadarData() {
  return {
    indicators: [
      { name: "准确率", max: 100 },
      { name: "精确率", max: 100 },
      { name: "召回率", max: 100 },
      { name: "F1分数", max: 100 },
      { name: "夏普比率", max: 2 },
      { name: "胜率", max: 100 },
    ],
    models: [
      {
        name: "LSTM",
        values: [68.5, 67.2, 69.8, 68.5, 1.42, 56.8],
        color: BLUE,
      },
      {
        name: "Transformer",
        values: [70.2, 69.5, 71.0, 70.2, 1.48, 58.2],
        color: PURPLE,
      },
      {
        name: "LightGBM",
        values: [65.2, 64.8, 65.6, 65.2, 1.28, 54.5],
        color: AMBER,
      },
      {
        name: "集成模型",
        values: [71.2, 70.5, 71.8, 71.2, 1.56, 59.5],
        color: GAIN_COLOR,
      },
    ],
  };
}
