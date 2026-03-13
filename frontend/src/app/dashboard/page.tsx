"use client";

import { useState, useEffect } from "react";
import {
  TrendingUp,
  Activity,
  Target,
  Brain,
  RefreshCw,
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Zap,
} from "lucide-react";
import api from "@/lib/api";

interface BacktestResult {
  model_id: string;
  model_type: string;
  symbol: string;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  direction_accuracy: number | null;
  win_rate: number | null;
  n_trades: number;
  excess_return: number | null;
}
interface BacktestSummary {
  summary: Record<
    string,
    {
      count: number;
      avg_sharpe: number | null;
      avg_return: number | null;
      avg_direction_accuracy: number | null;
    }
  >;
  best_models: BacktestResult[];
}
interface ModelInfo {
  model_id: string;
  name: string;
  model_type: string;
  model_type_display: string;
  symbol: string;
  val_loss: number | null;
  created_at: string;
}

const TYPE_NAMES: Record<string, string> = {
  lstm: "BiLSTM+Attn",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};
const fmtPct = (v: number | null) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "N/A";

function MetricCard({
  title,
  value,
  sub,
  up,
  icon: Icon,
}: {
  title: string;
  value: string;
  sub?: string;
  up?: boolean | null;
  icon: React.ElementType;
}) {
  return (
    <div className="t-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 mb-1">{title}</p>
          <h3 className="text-xl font-bold font-num text-gray-100">{value}</h3>
          {sub && (
            <div
              className={`flex items-center gap-1 mt-1.5 text-xs ${up === true ? "text-gain" : up === false ? "text-loss" : "text-gray-500"}`}
            >
              {up === true ? (
                <ArrowUpRight className="w-3 h-3" />
              ) : up === false ? (
                <ArrowDownRight className="w-3 h-3" />
              ) : null}
              <span>{sub}</span>
            </div>
          )}
        </div>
        <div className="p-2 rounded bg-accent-blue/10">
          <Icon className="w-5 h-5 text-accent-blue" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [summary, setSummary] = useState<BacktestSummary | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [r, s, m] = await Promise.all([
          api.get<{ items: BacktestResult[]; total: number }>("/backtest/"),
          api.get<BacktestSummary>("/backtest/summary"),
          api.get<{ items: ModelInfo[]; total: number }>("/models/"),
        ]);
        if (cancelled) return;
        setResults(r.items);
        setSummary(s);
        setModels(m.items);
      } catch (e: any) {
        if (!cancelled) setError(e.message || "加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading)
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-6 h-6 text-accent-blue animate-spin" />
        <span className="ml-3 text-gray-400 text-sm">加载系统数据...</span>
      </div>
    );
  if (error)
    return (
      <div className="t-card text-center py-12">
        <p className="text-loss mb-4 text-sm">{error}</p>
        <button onClick={() => window.location.reload()} className="t-btn">
          重试
        </button>
      </div>
    );

  const avg = (arr: number[]) =>
    arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
  const avgSharpe = avg(results.map((r) => r.sharpe_ratio || 0));
  const bestSharpe = results.length
    ? Math.max(...results.map((r) => r.sharpe_ratio || 0))
    : 0;
  const avgAcc = avg(results.map((r) => r.direction_accuracy || 0));
  const avgRet = avg(results.map((r) => r.total_return || 0));
  const symbols = new Set(results.map((r) => r.symbol));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">控制台概览</h1>
          <p className="text-gray-500 text-xs mt-1">
            {models.length} 个已训练模型，覆盖 {symbols.size} 只美股
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <CheckCircle className="w-3.5 h-3.5 text-gain" />
          系统运行正常
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          title="已训练模型"
          value={`${models.length}`}
          sub={`${symbols.size} 只股票 × 4 种模型`}
          icon={Brain}
        />
        <MetricCard
          title="平均夏普比率"
          value={avgSharpe.toFixed(2)}
          sub={avgSharpe > 1 ? "优秀" : avgSharpe > 0.5 ? "良好" : "一般"}
          up={avgSharpe > 0.5}
          icon={Target}
        />
        <MetricCard
          title="平均方向准确率"
          value={fmtPct(avgAcc)}
          sub={avgAcc > 0.5 ? "高于随机基准" : "接近随机"}
          up={avgAcc > 0.5}
          icon={Activity}
        />
        <MetricCard
          title="平均总收益"
          value={fmtPct(avgRet)}
          sub={`最佳夏普: ${bestSharpe.toFixed(2)}`}
          up={avgRet > 0 ? true : avgRet < 0 ? false : null}
          icon={TrendingUp}
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {summary && (
          <div className="t-card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              模型性能
            </h3>
            <div className="space-y-3">
              {Object.entries(summary.summary).map(([type, stats]) => (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded bg-accent-blue/10 flex items-center justify-center">
                      <Zap className="w-4 h-4 text-accent-blue" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-200">
                        {TYPE_NAMES[type] || type}
                      </div>
                      <div className="text-xs text-gray-500">
                        夏普: {stats.avg_sharpe?.toFixed(2) || "N/A"} | 准确率:{" "}
                        {fmtPct(stats.avg_direction_accuracy)}
                      </div>
                    </div>
                  </div>
                  <span
                    className={`t-badge ${(stats.avg_return || 0) > 0 ? "t-badge-gain" : "t-badge-loss"}`}
                  >
                    {fmtPct(stats.avg_return)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {summary && summary.best_models.length > 0 && (
          <div className="t-card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              最佳模型 (Sharpe)
            </h3>
            <div className="space-y-2">
              {summary.best_models.map((m, i) => (
                <div
                  key={m.model_id}
                  className="flex items-center justify-between p-2.5 rounded bg-terminal-hover"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? "bg-amber-400/20 text-amber-400" : i === 1 ? "bg-gray-300/20 text-gray-300" : i === 2 ? "bg-orange-400/20 text-orange-400" : "bg-terminal-border text-gray-500"}`}
                    >
                      {i + 1}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-200">
                        {TYPE_NAMES[m.model_type] || m.model_type} - {m.symbol}
                      </div>
                      <div className="text-xs text-gray-500">
                        收益 {fmtPct(m.total_return)}
                      </div>
                    </div>
                  </div>
                  <div className="text-accent-blue font-bold font-num text-sm">
                    {m.sharpe_ratio?.toFixed(2) || "N/A"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Symbol coverage */}
      <div className="t-card">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">股票覆盖</h3>
        <div className="overflow-x-auto">
          <table className="t-table">
            <thead>
              <tr>
                <th>股票</th>
                <th>模型数</th>
                <th>最佳夏普</th>
                <th>平均准确率</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(
                results.reduce<Record<string, BacktestResult[]>>((acc, r) => {
                  (acc[r.symbol] ??= []).push(r);
                  return acc;
                }, {}),
              )
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([sym, items]) => (
                  <tr key={sym}>
                    <td className="font-medium text-gray-200">{sym}</td>
                    <td>{items.length}</td>
                    <td className="text-accent-blue font-num">
                      {Math.max(
                        ...items.map((r) => r.sharpe_ratio || 0),
                      ).toFixed(2)}
                    </td>
                    <td className="text-amber-400 font-num">
                      {fmtPct(avg(items.map((r) => r.direction_accuracy || 0)))}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
