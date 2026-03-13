"use client";

import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { echarts } from "./echarts-setup";
import { GAIN_COLOR, LOSS_COLOR, BLUE, PURPLE } from "./theme";

interface KLineChartProps {
  data: {
    dates: string[];
    values: [number, number, number, number][];
    volumes: number[];
    ma5?: number[];
    ma20?: number[];
    ma60?: number[];
    signals?: { date: string; type: "buy" | "sell"; price: number }[];
  };
  height?: number;
  showVolume?: boolean;
  showMA?: boolean;
}

export function KLineChart({
  data,
  height = 500,
  showVolume = true,
  showMA = true,
}: KLineChartProps) {
  const option = useMemo(() => {
    const series: any[] = [
      {
        name: "K线",
        type: "candlestick",
        data: data.values,
        itemStyle: {
          color: GAIN_COLOR,
          color0: LOSS_COLOR,
          borderColor: GAIN_COLOR,
          borderColor0: LOSS_COLOR,
        },
      },
    ];

    if (showMA && data.ma5)
      series.push({
        name: "MA5",
        type: "line",
        data: data.ma5,
        smooth: true,
        lineStyle: { width: 1, color: BLUE },
        symbol: "none",
      });
    if (showMA && data.ma20)
      series.push({
        name: "MA20",
        type: "line",
        data: data.ma20,
        smooth: true,
        lineStyle: { width: 1, color: PURPLE },
        symbol: "none",
      });
    if (showMA && data.ma60)
      series.push({
        name: "MA60",
        type: "line",
        data: data.ma60,
        smooth: true,
        lineStyle: { width: 1, color: "#F59E0B" },
        symbol: "none",
      });

    const grids: any[] = [
      { left: 60, right: 20, top: 40, bottom: showVolume ? "28%" : 50 },
    ];
    const xAxes: any[] = [
      {
        type: "category",
        data: data.dates,
        axisLine: { lineStyle: { color: "#1F2937" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
    ];
    const yAxes: any[] = [
      {
        type: "value",
        scale: true,
        splitLine: { lineStyle: { color: "#1F293740" } },
        axisLabel: { color: "#6B7280", fontSize: 10 },
      },
    ];

    if (showVolume) {
      grids.push({ left: 60, right: 20, top: "76%", bottom: 30 });
      xAxes.push({
        type: "category",
        data: data.dates,
        gridIndex: 1,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: "#1F2937" } },
      });
      yAxes.push({
        type: "value",
        gridIndex: 1,
        splitLine: { show: false },
        axisLabel: { show: false },
      });
      series.push({
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: data.volumes.map((v, i) => ({
          value: v,
          itemStyle: {
            color:
              data.values[i]?.[1] >= data.values[i]?.[0]
                ? GAIN_COLOR + "60"
                : LOSS_COLOR + "60",
          },
        })),
      });
    }

    if (data.signals) {
      const buyData = data.signals
        .filter((s) => s.type === "buy")
        .map((s) => ({
          coord: [s.date, s.price],
          value: "B",
          itemStyle: { color: GAIN_COLOR },
          symbol: "triangle",
          symbolSize: 12,
          symbolRotate: 0,
        }));
      const sellData = data.signals
        .filter((s) => s.type === "sell")
        .map((s) => ({
          coord: [s.date, s.price],
          value: "S",
          itemStyle: { color: LOSS_COLOR },
          symbol: "triangle",
          symbolSize: 12,
          symbolRotate: 180,
        }));
      if (buyData.length || sellData.length) {
        series[0].markPoint = { data: [...buyData, ...sellData] };
      }
    }

    return {
      backgroundColor: "transparent",
      animation: false,
      legend: {
        data: ["K线", ...(showMA ? ["MA5", "MA20", "MA60"] : [])],
        top: 5,
        textStyle: { color: "#9CA3AF", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross", crossStyle: { color: "#374151" } },
        backgroundColor: "#1F2937",
        borderColor: "#374151",
        textStyle: { color: "#F9FAFB", fontSize: 11 },
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      series,
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 50,
          end: 100,
        },
      ],
    };
  }, [
    data.dates,
    data.values,
    data.volumes,
    data.ma5,
    data.ma20,
    data.ma60,
    data.signals,
    showVolume,
    showMA,
  ]);

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

export function generateMockKLineData(days = 120) {
  const dates: string[] = [],
    values: [number, number, number, number][] = [],
    volumes: number[] = [];
  const ma5: number[] = [],
    ma20: number[] = [],
    ma60: number[] = [];
  let price = 180;
  const base = new Date("2024-10-01");
  for (let i = 0; i < days; i++) {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
    const chg = (Math.random() - 0.48) * 4;
    const o = price,
      c = price + chg;
    const h = Math.max(o, c) + Math.random() * 2,
      l = Math.min(o, c) - Math.random() * 2;
    values.push([o, c, l, h]);
    volumes.push(Math.floor(3e7 + Math.random() * 3e7));
    price = c;
    const calc = (n: number) =>
      i >= n - 1
        ? values.slice(i - n + 1, i + 1).reduce((a, b) => a + b[1], 0) / n
        : c;
    ma5.push(calc(5));
    ma20.push(calc(20));
    ma60.push(calc(60));
  }
  const signals: { date: string; type: "buy" | "sell"; price: number }[] = [];
  for (let i = 10; i < days; i += Math.floor(Math.random() * 15) + 10) {
    signals.push({
      date: dates[i],
      type: Math.random() > 0.5 ? "buy" : "sell",
      price: values[i][Math.random() > 0.5 ? 3 : 2],
    });
  }
  return { dates, values, volumes, ma5, ma20, ma60, signals };
}
