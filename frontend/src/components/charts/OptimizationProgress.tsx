"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { BLUE, GAIN_COLOR } from "./theme";

interface OptimizationProgressProps {
  data: { trials: number[]; bestValues: number[]; currentValues: number[] };
  height?: number;
}

export function OptimizationProgress({
  data,
  height = 300,
}: OptimizationProgressProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: ["当前值", "最优值"],
        top: 5,
        textStyle: { color: "#9CA3AF", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: { left: 60, right: 20, top: 40, bottom: 40 },
      xAxis: {
        type: "category",
        data: data.trials,
        name: "Trial",
        nameLocation: "middle" as const,
        nameGap: 25,
        nameTextStyle: { color: "#6B7280" },
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        name: "夏普比率",
        nameLocation: "middle" as const,
        nameGap: 40,
        nameTextStyle: { color: "#6B7280" },
        axisLabel: { color: "#6B7280", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series: [
        {
          name: "当前值",
          type: "scatter",
          data: data.currentValues,
          symbolSize: 6,
          itemStyle: { color: BLUE + "90" },
        },
        {
          name: "最优值",
          type: "line",
          data: data.bestValues,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2.5, color: GAIN_COLOR },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: GAIN_COLOR + "30" },
              { offset: 1, color: GAIN_COLOR + "00" },
            ]),
          },
        },
      ],
    }),
    [data.trials, data.bestValues, data.currentValues],
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

export function generateMockOptimizationData(numTrials = 50) {
  const trials: number[] = [],
    bestValues: number[] = [],
    currentValues: number[] = [];
  let best = 1.0;
  for (let i = 1; i <= numTrials; i++) {
    trials.push(i);
    const current = 1.0 + Math.random() * 0.8 - 0.2;
    currentValues.push(current);
    best = Math.max(best, current);
    bestValues.push(best);
  }
  return { trials, bestValues, currentValues };
}
