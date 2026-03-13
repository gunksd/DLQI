"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { GAIN_COLOR, LOSS_COLOR } from "./theme";

interface HeatmapChartProps {
  data: {
    xLabels: string[];
    yLabels: string[];
    values: [number, number, number][]; // [xIndex, yIndex, value]
  };
  height?: number;
  valueFormatter?: (v: number) => string;
}

export function HeatmapChart({
  data,
  height = 350,
  valueFormatter,
}: HeatmapChartProps) {
  const option = useMemo(() => {
    const allValues = data.values.map((v) => v[2]);
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const fmt = valueFormatter ?? ((v: number) => v.toFixed(2));

    return {
      backgroundColor: "transparent",
      animation: false,
      tooltip: {
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
        formatter: (params: any) => {
          const d = params.data;
          return `<div style="font-size:11px"><b>${data.xLabels[d[0]]} / ${data.yLabels[d[1]]}</b><br/>值: ${fmt(d[2])}</div>`;
        },
      },
      grid: { left: 80, right: 40, top: 10, bottom: 40 },
      xAxis: {
        type: "category",
        data: data.xLabels,
        splitArea: { show: true },
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      yAxis: {
        type: "category",
        data: data.yLabels,
        splitArea: { show: true },
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        calculable: true,
        orient: "vertical",
        right: 0,
        top: "center",
        textStyle: { color: "#6B7280", fontSize: 10 },
        inRange: { color: [LOSS_COLOR, "#1F2937", GAIN_COLOR] },
      },
      series: [
        {
          type: "heatmap",
          data: data.values,
          label: {
            show: true,
            color: "#D1D5DB",
            fontSize: 10,
            formatter: (p: any) => fmt(p.data[2]),
          },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
          },
        },
      ],
    };
  }, [data.xLabels, data.yLabels, data.values, valueFormatter]);

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

export function generateMockHeatmapData() {
  const xLabels = ["LSTM", "Transformer", "LightGBM", "XGBoost", "集成模型"];
  const yLabels = ["准确率", "精确率", "召回率", "F1", "夏普比率", "最大回撤"];
  const values: [number, number, number][] = [];
  for (let x = 0; x < xLabels.length; x++) {
    for (let y = 0; y < yLabels.length; y++) {
      values.push([x, y, +(0.5 + Math.random() * 0.4).toFixed(3)]);
    }
  }
  return { xLabels, yLabels, values };
}
