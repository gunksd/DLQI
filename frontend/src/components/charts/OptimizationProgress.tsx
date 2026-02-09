"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface OptimizationProgressProps {
  data: {
    trials: number[];
    bestValues: number[];
    currentValues: number[];
  };
  height?: number;
}

export function OptimizationProgress({
  data,
  height = 300,
}: OptimizationProgressProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      legend: {
        data: ["当前值", "最优值"],
        top: 10,
        textStyle: { color: "#94a3b8" },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
        formatter: (params: any) => {
          const trial = params[0]?.axisValue;
          let result = `<div style="font-size: 12px;"><div style="margin-bottom: 4px;">Trial #${trial}</div>`;
          params.forEach((item: any) => {
            result += `<div>${item.seriesName}: <span style="color: ${item.color}">${item.value.toFixed(4)}</span></div>`;
          });
          result += "</div>";
          return result;
        },
      },
      grid: {
        left: "10%",
        right: "5%",
        top: 50,
        bottom: 40,
      },
      xAxis: {
        type: "category",
        name: "Trial",
        nameLocation: "middle" as const,
        nameGap: 25,
        nameTextStyle: { color: "#94a3b8" },
        data: data.trials,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: "夏普比率",
        nameLocation: "middle" as const,
        nameGap: 35,
        nameTextStyle: { color: "#94a3b8" },
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series: [
        {
          name: "当前值",
          type: "scatter",
          data: data.currentValues,
          symbolSize: 8,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#00f5ff" },
              { offset: 1, color: "rgba(0, 245, 255, 0.5)" },
            ]),
          },
        },
        {
          name: "最优值",
          type: "line",
          data: data.bestValues,
          smooth: true,
          lineStyle: { width: 3, color: "#00ff88" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(0, 255, 136, 0.3)" },
              { offset: 1, color: "rgba(0, 255, 136, 0)" },
            ]),
          },
          symbol: "none",
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

// 生成模拟优化进度数据
export function generateMockOptimizationData(numTrials: number = 50) {
  const trials: number[] = [];
  const bestValues: number[] = [];
  const currentValues: number[] = [];

  let best = 1.0;

  for (let i = 1; i <= numTrials; i++) {
    trials.push(i);

    // 当前试验值：在一定范围内随机
    const current = 1.0 + Math.random() * 0.8 - 0.2;
    currentValues.push(current);

    // 最优值：只增不减
    best = Math.max(best, current);
    bestValues.push(best);
  }

  return { trials, bestValues, currentValues };
}
