"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface ROCCurveProps {
  data: {
    models: {
      name: string;
      fpr: number[];
      tpr: number[];
      auc: number;
      color: string;
    }[];
  };
  height?: number;
}

export function ROCCurve({ data, height = 350 }: ROCCurveProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, "dark");

    const series: echarts.SeriesOption[] = data.models.map((model) => ({
      name: `${model.name} (AUC: ${model.auc.toFixed(2)})`,
      type: "line",
      data: model.fpr.map((fpr, i) => [fpr, model.tpr[i]]),
      smooth: true,
      lineStyle: { width: 2, color: model.color },
      symbol: "none",
    }));

    // 添加对角线（随机猜测）
    series.push({
      name: "随机猜测",
      type: "line",
      data: [
        [0, 0],
        [1, 1],
      ],
      lineStyle: { width: 1, color: "#64748b", type: "dashed" },
      symbol: "none",
    });

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      legend: {
        data: [
          ...data.models.map((m) => `${m.name} (AUC: ${m.auc.toFixed(2)})`),
          "随机猜测",
        ],
        top: 10,
        textStyle: { color: "#94a3b8", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "rgba(255, 255, 255, 0.1)",
        textStyle: { color: "#f1f5f9" },
        formatter: (params: any) => {
          let result = `<div style="font-size: 12px;">`;
          params.forEach((item: any) => {
            if (item.data) {
              result += `<div>${item.seriesName}: FPR=${item.data[0]?.toFixed(2)}, TPR=${item.data[1]?.toFixed(2)}</div>`;
            }
          });
          result += "</div>";
          return result;
        },
      },
      grid: {
        left: "12%",
        right: "5%",
        top: 60,
        bottom: 40,
      },
      xAxis: {
        type: "value",
        name: "假阳性率 (FPR)",
        nameLocation: "middle" as const,
        nameGap: 25,
        nameTextStyle: { color: "#94a3b8" },
        min: 0,
        max: 1,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      yAxis: {
        type: "value",
        name: "真阳性率 (TPR)",
        nameLocation: "middle" as const,
        nameGap: 35,
        nameTextStyle: { color: "#94a3b8" },
        min: 0,
        max: 1,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8" },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series,
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

// 生成模拟ROC数据
export function generateMockROCData() {
  const generateROC = (auc: number) => {
    const points = 50;
    const fpr: number[] = [];
    const tpr: number[] = [];

    for (let i = 0; i <= points; i++) {
      const x = i / points;
      // 使用幂函数模拟ROC曲线形状
      const y = Math.pow(x, 1 / (auc * 2));
      fpr.push(x);
      tpr.push(Math.min(1, y));
    }

    return { fpr, tpr };
  };

  return {
    models: [
      { name: "LSTM", ...generateROC(0.72), auc: 0.72, color: "#00f5ff" },
      { name: "Transformer", ...generateROC(0.74), auc: 0.74, color: "#bf00ff" },
      { name: "LightGBM", ...generateROC(0.68), auc: 0.68, color: "#ffa502" },
      { name: "集成模型", ...generateROC(0.76), auc: 0.76, color: "#00ff88" },
    ],
  };
}
