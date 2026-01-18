"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface DistributionChartProps {
  data: {
    bins: string[];
    counts: number[];
  };
  height?: number;
  title?: string;
}

export function DistributionChart({
  data,
  height = 250,
  title = "收益分布",
}: DistributionChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      title: {
        text: title,
        left: "center",
        top: 0,
        textStyle: { color: "#f1f5f9", fontSize: 14 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
      },
      grid: {
        left: "10%",
        right: "5%",
        top: 40,
        bottom: 30,
      },
      xAxis: {
        type: "category",
        data: data.bins,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series: [
        {
          type: "bar",
          data: data.counts.map((count, index) => ({
            value: count,
            itemStyle: {
              color:
                parseFloat(data.bins[index]) >= 0
                  ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: "#00ff88" },
                      { offset: 1, color: "rgba(0, 255, 136, 0.3)" },
                    ])
                  : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: "#ff4757" },
                      { offset: 1, color: "rgba(255, 71, 87, 0.3)" },
                    ]),
            },
          })),
          barWidth: "60%",
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
  }, [data, title]);

  return (
    <div
      ref={chartRef}
      style={{ width: "100%", height }}
      className="rounded-clay-sm"
    />
  );
}

// 生成模拟分布数据
export function generateMockDistributionData() {
  const bins = ["-5%", "-4%", "-3%", "-2%", "-1%", "0%", "1%", "2%", "3%", "4%", "5%"];
  const counts = bins.map(() => Math.floor(Math.random() * 50) + 10);

  // 使分布呈正态形状
  const center = Math.floor(bins.length / 2);
  for (let i = 0; i < bins.length; i++) {
    const distance = Math.abs(i - center);
    counts[i] = Math.floor(counts[i] * (1 - distance * 0.15));
  }

  return { bins, counts };
}
