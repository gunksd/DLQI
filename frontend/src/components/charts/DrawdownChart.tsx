"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface DrawdownChartProps {
  data: {
    dates: string[];
    drawdown: number[];
  };
  height?: number;
}

export function DrawdownChart({ data, height = 250 }: DrawdownChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
        formatter: (params: any) => {
          const data = params[0];
          return `
            <div style="font-size: 12px;">
              <div style="margin-bottom: 4px;">${data.axisValue}</div>
              <div>回撤: <span style="color: #ff4757">${(data.value * 100).toFixed(2)}%</span></div>
            </div>
          `;
        },
      },
      grid: {
        left: "10%",
        right: "5%",
        top: 20,
        bottom: 40,
      },
      xAxis: {
        type: "category",
        data: data.dates,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        max: 0,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: {
          color: "#94a3b8",
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series: [
        {
          type: "line",
          data: data.drawdown,
          smooth: true,
          lineStyle: { width: 2, color: "#ff4757" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(255, 71, 87, 0)" },
              { offset: 1, color: "rgba(255, 71, 87, 0.3)" },
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

// 生成模拟回撤数据
export function generateMockDrawdownData(days: number = 365) {
  const dates: string[] = [];
  const drawdown: number[] = [];

  let peak = 1;
  let current = 1;
  const baseDate = new Date("2024-01-01");

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    dates.push(date.toISOString().split("T")[0]);

    // 模拟收益变化
    current *= 1 + (Math.random() - 0.48) * 0.02;
    peak = Math.max(peak, current);
    const dd = (current - peak) / peak;
    drawdown.push(dd);
  }

  return { dates, drawdown };
}
