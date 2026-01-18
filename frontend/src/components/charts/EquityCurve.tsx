"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface EquityCurveProps {
  data: {
    dates: string[];
    strategy: number[];
    benchmark: number[];
  };
  height?: number;
}

export function EquityCurve({ data, height = 400 }: EquityCurveProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      legend: {
        data: ["策略收益", "基准收益"],
        top: 10,
        textStyle: { color: "#94a3b8" },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
        formatter: (params: any) => {
          const date = params[0]?.axisValue;
          let result = `<div style="font-size: 12px;"><div style="margin-bottom: 4px;">${date}</div>`;
          params.forEach((item: any) => {
            result += `<div>${item.seriesName}: <span style="color: ${item.color}">${(item.value * 100).toFixed(2)}%</span></div>`;
          });
          result += "</div>";
          return result;
        },
      },
      grid: {
        left: "10%",
        right: "5%",
        top: 60,
        bottom: 60,
      },
      xAxis: {
        type: "category",
        data: data.dates,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: {
          color: "#94a3b8",
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      dataZoom: [
        {
          type: "inside",
          start: 0,
          end: 100,
        },
        {
          show: true,
          type: "slider",
          bottom: 10,
          borderColor: "#334155",
          fillerColor: "rgba(59, 130, 246, 0.2)",
          handleStyle: { color: "#3b82f6" },
          textStyle: { color: "#94a3b8" },
        },
      ],
      series: [
        {
          name: "策略收益",
          type: "line",
          data: data.strategy,
          smooth: true,
          lineStyle: { width: 2, color: "#00f5ff" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(0, 245, 255, 0.3)" },
              { offset: 1, color: "rgba(0, 245, 255, 0)" },
            ]),
          },
          symbol: "none",
        },
        {
          name: "基准收益",
          type: "line",
          data: data.benchmark,
          smooth: true,
          lineStyle: { width: 2, color: "#64748b", type: "dashed" },
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

// 生成模拟收益曲线数据
export function generateMockEquityData(days: number = 365) {
  const dates: string[] = [];
  const strategy: number[] = [];
  const benchmark: number[] = [];

  let strategyValue = 0;
  let benchmarkValue = 0;
  const baseDate = new Date("2024-01-01");

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    dates.push(date.toISOString().split("T")[0]);

    // 策略收益：更高的增长率和较低的波动
    strategyValue += (Math.random() - 0.45) * 0.015;
    // 基准收益：较低的增长率
    benchmarkValue += (Math.random() - 0.48) * 0.012;

    strategy.push(strategyValue);
    benchmark.push(benchmarkValue);
  }

  return { dates, strategy, benchmark };
}
