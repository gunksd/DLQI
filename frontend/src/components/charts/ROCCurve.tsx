"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { BLUE, PURPLE, AMBER, GAIN_COLOR } from "./theme";

interface ROCCurveProps {
  data: {
    models: {
      name: string;
      fpr: number[];
      tpr: number[];
      auc: number;
      color: string;
    }[];
  };
  height?: number;
}

export function ROCCurve({ data, height = 350 }: ROCCurveProps) {
  const option = useMemo(() => {
    const series: any[] = data.models.map((m) => ({
      name: `${m.name} (AUC: ${m.auc.toFixed(2)})`,
      type: "line",
      data: m.fpr.map((fpr, i) => [fpr, m.tpr[i]]),
      smooth: true,
      symbol: "none",
      lineStyle: { width: 2, color: m.color },
    }));
    series.push({
      name: "随机猜测",
      type: "line",
      data: [
        [0, 0],
        [1, 1],
      ],
      lineStyle: { width: 1, color: "#374151", type: "dashed" },
      symbol: "none",
    });

    return {
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: [
          ...data.models.map((m) => `${m.name} (AUC: ${m.auc.toFixed(2)})`),
          "随机猜测",
        ],
        top: 5,
        textStyle: { color: "#9CA3AF", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: { left: 55, right: 20, top: 50, bottom: 40 },
      xAxis: {
        type: "value",
        name: "FPR",
        nameLocation: "middle" as const,
        nameGap: 25,
        nameTextStyle: { color: "#6B7280" },
        min: 0,
        max: 1,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      yAxis: {
        type: "value",
        name: "TPR",
        nameLocation: "middle" as const,
        nameGap: 35,
        nameTextStyle: { color: "#6B7280" },
        min: 0,
        max: 1,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series,
    };
  }, [data.models]);

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

export function generateMockROCData() {
  const genROC = (auc: number) => {
    const fpr: number[] = [],
      tpr: number[] = [];
    for (let i = 0; i <= 50; i++) {
      const x = i / 50;
      fpr.push(x);
      tpr.push(Math.min(1, Math.pow(x, 1 / (auc * 2))));
    }
    return { fpr, tpr };
  };
  return {
    models: [
      { name: "LSTM", ...genROC(0.72), auc: 0.72, color: BLUE },
      { name: "Transformer", ...genROC(0.74), auc: 0.74, color: PURPLE },
      { name: "LightGBM", ...genROC(0.68), auc: 0.68, color: AMBER },
      { name: "集成模型", ...genROC(0.76), auc: 0.76, color: GAIN_COLOR },
    ],
  };
}
