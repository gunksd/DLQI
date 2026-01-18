"use client";

import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";

interface KLineChartProps {
  data: {
    dates: string[];
    values: [number, number, number, number][]; // [open, close, low, high]
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
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化图表
    chartInstance.current = echarts.init(chartRef.current, "dark");

    // 计算涨跌颜色
    const upColor = "#00ff88";
    const downColor = "#ff4757";

    // 构建系列数据
    const series: echarts.SeriesOption[] = [
      {
        name: "K线",
        type: "candlestick",
        data: data.values,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor,
        },
        markPoint: data.signals
          ? {
              data: data.signals.map((signal) => ({
                name: signal.type === "buy" ? "买入" : "卖出",
                coord: [signal.date, signal.price],
                value: signal.type === "buy" ? "B" : "S",
                itemStyle: {
                  color: signal.type === "buy" ? upColor : downColor,
                },
                symbol: signal.type === "buy" ? "arrow" : "arrow",
                symbolRotate: signal.type === "buy" ? 0 : 180,
                symbolSize: 20,
              })),
            }
          : undefined,
      },
    ];

    // 添加均线
    if (showMA && data.ma5) {
      series.push({
        name: "MA5",
        type: "line",
        data: data.ma5,
        smooth: true,
        lineStyle: { width: 1, color: "#ffa502" },
        symbol: "none",
      });
    }
    if (showMA && data.ma20) {
      series.push({
        name: "MA20",
        type: "line",
        data: data.ma20,
        smooth: true,
        lineStyle: { width: 1, color: "#00f5ff" },
        symbol: "none",
      });
    }
    if (showMA && data.ma60) {
      series.push({
        name: "MA60",
        type: "line",
        data: data.ma60,
        smooth: true,
        lineStyle: { width: 1, color: "#bf00ff" },
        symbol: "none",
      });
    }

    // 配置选项
    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      animation: true,
      legend: {
        data: ["K线", ...(showMA ? ["MA5", "MA20", "MA60"] : [])],
        top: 10,
        textStyle: { color: "#94a3b8" },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
        },
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
        formatter: (params: any) => {
          const data = params[0];
          if (!data) return "";
          const value = data.data;
          return `
            <div style="font-size: 12px;">
              <div style="margin-bottom: 4px;">${data.axisValue}</div>
              <div>开盘: <span style="color: #00f5ff">${value[1]}</span></div>
              <div>收盘: <span style="color: #00f5ff">${value[2]}</span></div>
              <div>最低: <span style="color: #ff4757">${value[3]}</span></div>
              <div>最高: <span style="color: #00ff88">${value[4]}</span></div>
            </div>
          `;
        },
      },
      grid: showVolume
        ? [
            { left: "10%", right: "8%", top: 60, height: "50%" },
            { left: "10%", right: "8%", top: "70%", height: "16%" },
          ]
        : [{ left: "10%", right: "8%", top: 60, bottom: 60 }],
      xAxis: showVolume
        ? [
            {
              type: "category",
              data: data.dates,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { color: "#94a3b8" },
              splitLine: { show: false },
            },
            {
              type: "category",
              gridIndex: 1,
              data: data.dates,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { show: false },
              splitLine: { show: false },
            },
          ]
        : [
            {
              type: "category",
              data: data.dates,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { color: "#94a3b8" },
              splitLine: { show: false },
            },
          ],
      yAxis: showVolume
        ? [
            {
              scale: true,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { color: "#94a3b8" },
              splitLine: { lineStyle: { color: "#1e293b" } },
            },
            {
              scale: true,
              gridIndex: 1,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { show: false },
              splitLine: { show: false },
            },
          ]
        : [
            {
              scale: true,
              axisLine: { lineStyle: { color: "#334155" } },
              axisLabel: { color: "#94a3b8" },
              splitLine: { lineStyle: { color: "#1e293b" } },
            },
          ],
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 50,
          end: 100,
        },
        {
          show: true,
          xAxisIndex: showVolume ? [0, 1] : [0],
          type: "slider",
          bottom: 10,
          start: 50,
          end: 100,
          borderColor: "#334155",
          fillerColor: "rgba(59, 130, 246, 0.2)",
          handleStyle: { color: "#3b82f6" },
          textStyle: { color: "#94a3b8" },
        },
      ],
      series: showVolume
        ? [
            ...series,
            {
              name: "成交量",
              type: "bar",
              xAxisIndex: 1,
              yAxisIndex: 1,
              data: data.volumes.map((v, i) => ({
                value: v,
                itemStyle: {
                  color:
                    data.values[i][1] >= data.values[i][0] ? upColor : downColor,
                },
              })),
            },
          ]
        : series,
    };

    chartInstance.current.setOption(option);

    // 响应式调整
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, [data, showVolume, showMA]);

  return (
    <div
      ref={chartRef}
      style={{ width: "100%", height }}
      className="rounded-clay-sm"
    />
  );
}

// 生成模拟K线数据
export function generateMockKLineData(days: number = 100) {
  const dates: string[] = [];
  const values: [number, number, number, number][] = [];
  const volumes: number[] = [];
  const ma5: number[] = [];
  const ma20: number[] = [];
  const ma60: number[] = [];

  let basePrice = 180;
  const baseDate = new Date("2024-10-01");

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    dates.push(date.toISOString().split("T")[0]);

    // 随机生成价格波动
    const change = (Math.random() - 0.48) * 4;
    const open = basePrice;
    const close = basePrice + change;
    const high = Math.max(open, close) + Math.random() * 2;
    const low = Math.min(open, close) - Math.random() * 2;

    values.push([open, close, low, high]);
    volumes.push(Math.floor(30000000 + Math.random() * 30000000));

    basePrice = close;

    // 计算均线
    if (i >= 4) {
      const ma5Value = values.slice(i - 4, i + 1).reduce((a, b) => a + b[1], 0) / 5;
      ma5.push(ma5Value);
    } else {
      ma5.push(close);
    }

    if (i >= 19) {
      const ma20Value = values.slice(i - 19, i + 1).reduce((a, b) => a + b[1], 0) / 20;
      ma20.push(ma20Value);
    } else {
      ma20.push(close);
    }

    if (i >= 59) {
      const ma60Value = values.slice(i - 59, i + 1).reduce((a, b) => a + b[1], 0) / 60;
      ma60.push(ma60Value);
    } else {
      ma60.push(close);
    }
  }

  // 生成交易信号
  const signals: { date: string; type: "buy" | "sell"; price: number }[] = [];
  for (let i = 0; i < days; i += Math.floor(Math.random() * 15) + 10) {
    if (i > 0 && i < days) {
      signals.push({
        date: dates[i],
        type: Math.random() > 0.5 ? "buy" : "sell",
        price: values[i][Math.random() > 0.5 ? 3 : 2],
      });
    }
  }

  return { dates, values, volumes, ma5, ma20, ma60, signals };
}
