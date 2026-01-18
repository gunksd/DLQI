"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

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
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      legend: {
        data: ["VaR (95%)", "VaR (99%)", "实际损失"],
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
        top: 50,
        bottom: 40,
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
          name: "VaR (95%)",
          type: "line",
          data: data.var95,
          smooth: true,
          lineStyle: { width: 2, color: "#00f5ff" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(0, 245, 255, 0)" },
              { offset: 1, color: "rgba(0, 245, 255, 0.2)" },
            ]),
          },
          symbol: "none",
        },
        {
          name: "VaR (99%)",
          type: "line",
          data: data.var99,
          smooth: true,
          lineStyle: { width: 2, color: "#bf00ff" },
          symbol: "none",
        },
        {
          name: "实际损失",
          type: "scatter",
          data: data.actualLoss.map((loss, i) => ({
            value: loss,
            itemStyle: {
              color: loss < data.var99[i] ? "#ff4757" : "#00ff88",
            },
          })),
          symbolSize: 6,
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

// 生成模拟VaR数据
export function generateMockVaRData(days: number = 60) {
  const dates: string[] = [];
  const var95: number[] = [];
  const var99: number[] = [];
  const actualLoss: number[] = [];

  const baseDate = new Date("2024-11-01");

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    dates.push(date.toISOString().split("T")[0]);

    // VaR随时间波动
    const baseVar = -0.02 + Math.sin(i / 10) * 0.005 + (Math.random() - 0.5) * 0.005;
    var95.push(baseVar);
    var99.push(baseVar * 1.5);

    // 实际损失：大部分在VaR内，偶尔超出
    const loss = (Math.random() - 0.6) * 0.03;
    actualLoss.push(Math.min(0, loss));
  }

  return { dates, var95, var99, actualLoss };
}
