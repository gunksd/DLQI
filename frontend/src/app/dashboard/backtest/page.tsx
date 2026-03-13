"use client";

import { useState, useEffect } from "react";
import {
  TrendingUp,
  RefreshCw,
  Clock,
  Target,
  Activity,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import api from "@/lib/api";

interface BacktestResult {
  id: number;
  model_id: string;
  model_type: string;
  symbol: string;
  total_return: number | null;
  annual_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  direction_accuracy: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  n_trades: number;
  benchmark_return: number | null;
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
interface HeatmapData {
  symbols: string[];
  model_types: string[];
  data: Array<{
    model_type: string;
    symbol: string;
    sharpe_ratio: number;
    total_return: number;
    direction_accuracy: number;
  }>;
}

const TYPE_NAMES: Record<string, string> = {
  lstm: "LSTM",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};
const fmtPct = (v: number | null) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "-";

function SummaryCard({
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

export default function BacktestPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [summary, setSummary] = useState<BacktestSummary | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [r, s, h] = await Promise.all([
          api.get<{ items: BacktestResult[]; total: number }>("/backtest/"),
          api.get<BacktestSummary>("/backtest/summary"),
          api.get<HeatmapData>("/backtest/heatmap"),
        ]);
        if (cancelled) return;
        setResults(r.items);
        setSummary(s);
        setHeatmap(h);
        setSymbols(Array.from(new Set(r.items.map((r) => r.symbol))).sort());
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
        <span className="ml-3 text-gray-400 text-sm">加载回测数据...</span>
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
  const filtered = selectedSymbol
    ? results.filter((r) => r.symbol === selectedSymbol)
    : results;

  const getHeatColor = (v: number) =>
    v >= 2
      ? "bg-gain"
      : v >= 1
        ? "bg-gain/60"
        : v >= 0.5
          ? "bg-amber-400/50"
          : v >= 0
            ? "bg-orange-400/40"
            : "bg-loss/50";

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">回测结果</h1>
          <p className="text-gray-500 text-xs mt-1">
            {results.length} 条记录，{symbols.length} 只股票
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Clock className="w-3.5 h-3.5" />5 只美股 × 4 种模型
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryCard
          title="平均夏普"
          value={avgSharpe.toFixed(2)}
          sub="所有模型均值"
          up={avgSharpe > 1 ? true : null}
          icon={Target}
        />
        <SummaryCard
          title="最佳夏普"
          value={bestSharpe.toFixed(2)}
          sub="单模型最高"
          up={true}
          icon={TrendingUp}
        />
        <SummaryCard
          title="平均方向准确率"
          value={fmtPct(avgAcc)}
          sub={avgAcc > 0.5 ? "高于随机" : "接近随机"}
          up={avgAcc > 0.5}
          icon={Percent}
        />
        <SummaryCard
          title="平均总收益"
          value={fmtPct(avgRet)}
          sub="全部模型"
          up={avgRet > 0 ? true : avgRet < 0 ? false : null}
          icon={Activity}
        />
      </div>

      {/* Model type summary */}
      {summary && (
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            模型类型对比
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(summary.summary).map(([type, stats]) => (
              <div
                key={type}
                className="p-3 rounded bg-terminal-hover text-center"
              >
                <div className="text-base font-bold text-gray-100 mb-1.5">
                  {TYPE_NAMES[type] || type}
                </div>
                <div className="space-y-1 text-xs">
                  <div>
                    <span className="text-gray-500">夏普: </span>
                    <span className="text-accent-blue font-num">
                      {stats.avg_sharpe?.toFixed(2) || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">收益: </span>
                    <span
                      className={`font-num ${(stats.avg_return || 0) >= 0 ? "text-gain" : "text-loss"}`}
                    >
                      {fmtPct(stats.avg_return)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">准确: </span>
                    <span className="text-amber-400 font-num">
                      {fmtPct(stats.avg_direction_accuracy)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Heatmap */}
      {heatmap && heatmap.symbols.length > 0 && (
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            Sharpe 热力图
          </h3>
          <div className="overflow-x-auto">
            <div className="inline-block">
              <div className="flex">
                <div className="w-24" />
                {heatmap.symbols.map((s) => (
                  <div
                    key={s}
                    className="w-20 text-center text-xs text-gray-500 py-1.5"
                  >
                    {s}
                  </div>
                ))}
              </div>
              {heatmap.model_types.map((mt) => (
                <div key={mt} className="flex items-center">
                  <div className="w-24 text-xs text-gray-500 pr-2 text-right">
                    {TYPE_NAMES[mt] || mt}
                  </div>
                  {heatmap.symbols.map((sym) => {
                    const val =
                      heatmap.data.find(
                        (d) => d.model_type === mt && d.symbol === sym,
                      )?.sharpe_ratio || 0;
                    return (
                      <div
                        key={sym}
                        className={`w-20 h-10 flex items-center justify-center text-xs font-num font-medium text-white ${getHeatColor(val)}`}
                      >
                        {val.toFixed(2)}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top 5 + Table */}
      <div className="grid lg:grid-cols-3 gap-4">
        {summary && summary.best_models.length > 0 && (
          <div className="t-card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Top 5 (Sharpe)
            </h3>
            <div className="space-y-2">
              {summary.best_models.map((m, i) => (
                <div
                  key={m.model_id}
                  className="flex items-center justify-between p-2.5 rounded bg-terminal-hover"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? "bg-amber-400/20 text-amber-400" : i === 1 ? "bg-gray-300/20 text-gray-300" : i === 2 ? "bg-orange-400/20 text-orange-400" : "bg-terminal-border text-gray-500"}`}
                    >
                      {i + 1}
                    </div>
                    <div>
                      <div className="text-sm text-gray-200">
                        {m.model_type.toUpperCase()} - {m.symbol}
                      </div>
                      <div className="text-xs text-gray-500">
                        收益 {fmtPct(m.total_return)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-accent-blue font-bold font-num text-sm">
                      {m.sharpe_ratio?.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">
                      准确 {fmtPct(m.direction_accuracy)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="lg:col-span-2 t-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-200">
              全部回测结果
            </h3>
            <select
              className="t-select !py-1.5 text-xs w-28"
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
            >
              <option value="">全部</option>
              {symbols.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="t-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th>股票</th>
                  <th>年化收益</th>
                  <th>夏普</th>
                  <th>Sortino</th>
                  <th>最大回撤</th>
                  <th>方向准确率</th>
                  <th>交易次数</th>
                  <th>超额收益</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.model_id}>
                    <td className="font-medium text-gray-200">
                      {r.model_type.toUpperCase()}
                    </td>
                    <td>{r.symbol}</td>
                    <td
                      className={`font-num ${(r.annual_return || 0) >= 0 ? "text-gain" : "text-loss"}`}
                    >
                      {fmtPct(r.annual_return)}
                    </td>
                    <td className="text-accent-blue font-num">
                      {r.sharpe_ratio?.toFixed(2) ?? "-"}
                    </td>
                    <td className="text-accent-cyan font-num">
                      {r.sortino_ratio?.toFixed(2) ?? "-"}
                    </td>
                    <td className="text-loss font-num">
                      {fmtPct(r.max_drawdown)}
                    </td>
                    <td className="text-amber-400 font-num">
                      {fmtPct(r.direction_accuracy)}
                    </td>
                    <td>{r.n_trades}</td>
                    <td
                      className={`font-num ${(r.excess_return || 0) >= 0 ? "text-gain" : "text-loss"}`}
                    >
                      {fmtPct(r.excess_return)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
