"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface RadarChartProps {
  data: {
    indicators: { name: string; max: number }[];
    models: {
      name: string;
      values: number[];
      color: string;
    }[];
  };
  height?: number;
}

export function RadarChart({ data, height = 350 }: RadarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      legend: {
        data: data.models.map((m) => m.name),
        top: 10,
        textStyle: { color: "#94a3b8" },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
      },
      radar: {
        indicator: data.indicators,
        shape: "polygon",
        splitNumber: 5,
        axisName: {
          color: "#94a3b8",
          fontSize: 11,
        },
        splitLine: {
          lineStyle: { color: "#334155" },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ["rgba(30, 41, 59, 0.5)", "rgba(30, 41, 59, 0.3)"],
          },
        },
        axisLine: {
          lineStyle: { color: "#334155" },
        },
      },
      series: [
        {
          type: "radar",
          data: data.models.map((model) => ({
            name: model.name,
            value: model.values,
            lineStyle: { width: 2, color: model.color },
            areaStyle: { color: `${model.color}33` },
            itemStyle: { color: model.color },
          })),
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, [data]);

  return (
    <div
      ref={chartRef}
      style={{ width: "100%", height }}
      className="rounded-clay-sm"
    />
  );
}

// 生成模拟雷达图数据
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
        color: "#00f5ff",
      },
      {
        name: "Transformer",
        values: [70.2, 69.5, 71.0, 70.2, 1.48, 58.2],
        color: "#bf00ff",
      },
      {
        name: "LightGBM",
        values: [65.2, 64.8, 65.6, 65.2, 1.28, 54.5],
        color: "#ffa502",
      },
      {
        name: "集成模型",
        values: [71.2, 70.5, 71.8, 71.2, 1.56, 59.5],
        color: "#00ff88",
      },
    ],
  };
}
