"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { GAIN_COLOR, LOSS_COLOR } from "./theme";

interface DistributionChartProps {
  data: { bins: string[]; counts: number[] };
  height?: number;
  title?: string;
}

export function DistributionChart({
  data,
  height = 250,
  title,
}: DistributionChartProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      animation: false,
      ...(title
        ? {
            title: {
              text: title,
              left: "center",
              top: 0,
              textStyle: { color: "#F9FAFB", fontSize: 13, fontWeight: 500 },
            },
          }
        : {}),
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: { left: 50, right: 20, top: title ? 35 : 15, bottom: 30 },
      xAxis: {
        type: "category",
        data: data.bins,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#6B7280", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1F293740" } },
      },
      series: [
        {
          type: "bar",
          barWidth: "60%",
          data: data.counts.map((count, i) => ({
            value: count,
            itemStyle: {
              color:
                parseFloat(data.bins[i]) >= 0
                  ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: GAIN_COLOR },
                      { offset: 1, color: GAIN_COLOR + "40" },
                    ])
                  : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: LOSS_COLOR },
                      { offset: 1, color: LOSS_COLOR + "40" },
                    ]),
            },
          })),
        },
      ],
    }),
    [data.bins, data.counts, title],
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

export function generateMockDistributionData() {
  const bins = [
    "-5%",
    "-4%",
    "-3%",
    "-2%",
    "-1%",
    "0%",
    "1%",
    "2%",
    "3%",
    "4%",
    "5%",
  ];
  const counts = bins.map(() => Math.floor(Math.random() * 50) + 10);
  const center = Math.floor(bins.length / 2);
  for (let i = 0; i < bins.length; i++) {
    counts[i] = Math.floor(counts[i] * (1 - Math.abs(i - center) * 0.15));
  }
  return { bins, counts };
}
