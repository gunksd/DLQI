"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Clock,
  Target,
  Activity,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import api from "@/lib/api";

// ==================== 类型定义 ====================

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
  summary: Record<string, {
    count: number;
    avg_sharpe: number | null;
    avg_return: number | null;
    avg_direction_accuracy: number | null;
  }>;
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

// ==================== 汇总卡片 ====================

function SummaryCard({
  title, value, subtitle, changeType, icon: Icon, delay = 0,
}: {
  title: string; value: string; subtitle?: string;
  changeType?: "up" | "down" | "neutral"; icon: React.ElementType; delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }} className="clay-card"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100">{value}</h3>
          {subtitle && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              changeType === "up" ? "text-neon-green" : changeType === "down" ? "text-red-400" : "text-slate-400"
            }`}>
              {changeType === "up" ? <ArrowUpRight className="w-4 h-4" /> :
               changeType === "down" ? <ArrowDownRight className="w-4 h-4" /> : null}
              <span>{subtitle}</span>
            </div>
          )}
        </div>
        <div className="p-3 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20">
          <Icon className="w-6 h-6 text-neon-blue" />
        </div>
      </div>
    </motion.div>
  );
}

// ==================== 回测结果表格 ====================

function ResultsTable({ results, selectedSymbol, setSelectedSymbol, symbols }: {
  results: BacktestResult[];
  selectedSymbol: string;
  setSelectedSymbol: (s: string) => void;
  symbols: string[];
}) {
  const filtered = selectedSymbol
    ? results.filter((r) => r.symbol === selectedSymbol)
    : results;

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">全部回测结果</h3>
        <select
          className="clay-select !py-2 !px-3 text-sm w-32"
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
        >
          <option value="">全部</option>
          {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="clay-table">
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
                <td className="font-medium text-slate-200">{r.model_type.toUpperCase()}</td>
                <td>{r.symbol}</td>
                <td className={`${(r.annual_return || 0) >= 0 ? "text-neon-green" : "text-red-400"}`}>
                  {r.annual_return != null ? `${(r.annual_return * 100).toFixed(1)}%` : "-"}
                </td>
                <td className="text-neon-blue">
                  {r.sharpe_ratio != null ? r.sharpe_ratio.toFixed(2) : "-"}
                </td>
                <td className="text-cyan-400">
                  {r.sortino_ratio != null ? r.sortino_ratio.toFixed(2) : "-"}
                </td>
                <td className="text-red-400">
                  {r.max_drawdown != null ? `${(r.max_drawdown * 100).toFixed(1)}%` : "-"}
                </td>
                <td className="text-yellow-400">
                  {r.direction_accuracy != null ? `${(r.direction_accuracy * 100).toFixed(1)}%` : "-"}
                </td>
                <td>{r.n_trades}</td>
                <td className={`${(r.excess_return || 0) >= 0 ? "text-neon-green" : "text-red-400"}`}>
                  {r.excess_return != null ? `${(r.excess_return * 100).toFixed(1)}%` : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== 模型类型对比 ====================

function ModelTypeSummary({ summary }: { summary: BacktestSummary["summary"] }) {
  const types = Object.entries(summary);
  if (types.length === 0) return null;

  const typeNames: Record<string, string> = {
    lstm: "LSTM", transformer: "Transformer",
    lightgbm: "LightGBM", xgboost: "XGBoost",
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">模型类型对比</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {types.map(([type, stats]) => (
          <div key={type} className="p-4 rounded-clay-sm bg-dark-800/50 text-center">
            <div className="text-lg font-bold text-slate-100 mb-2">
              {typeNames[type] || type}
            </div>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-slate-500">平均夏普: </span>
                <span className="text-neon-blue font-medium">
                  {stats.avg_sharpe?.toFixed(2) || "N/A"}
                </span>
              </div>
              <div>
                <span className="text-slate-500">平均收益: </span>
                <span className={`font-medium ${(stats.avg_return || 0) >= 0 ? "text-neon-green" : "text-red-400"}`}>
                  {stats.avg_return != null ? `${(stats.avg_return * 100).toFixed(1)}%` : "N/A"}
                </span>
              </div>
              <div>
                <span className="text-slate-500">方向准确: </span>
                <span className="text-yellow-400 font-medium">
                  {stats.avg_direction_accuracy != null ? `${(stats.avg_direction_accuracy * 100).toFixed(1)}%` : "N/A"}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== Sharpe 热力图 ====================

function SharpeHeatmap({ data }: { data: HeatmapData }) {
  if (!data.symbols.length) return null;

  const getColor = (sharpe: number) => {
    if (sharpe >= 2) return "bg-neon-green";
    if (sharpe >= 1) return "bg-neon-green/60";
    if (sharpe >= 0.5) return "bg-yellow-400/50";
    if (sharpe >= 0) return "bg-orange-400/40";
    return "bg-red-500/50";
  };

  const getValue = (mt: string, sym: string) => {
    const item = data.data.find((d) => d.model_type === mt && d.symbol === sym);
    return item?.sharpe_ratio || 0;
  };

  const typeNames: Record<string, string> = {
    lstm: "LSTM", transformer: "Transformer",
    lightgbm: "LightGBM", xgboost: "XGBoost",
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">Sharpe 热力图</h3>
      <div className="overflow-x-auto">
        <div className="inline-block">
          <div className="flex">
            <div className="w-24"></div>
            {data.symbols.map((s) => (
              <div key={s} className="w-20 text-center text-xs text-slate-400 py-2">{s}</div>
            ))}
          </div>
          {data.model_types.map((mt) => (
            <div key={mt} className="flex items-center">
              <div className="w-24 text-xs text-slate-400 pr-2 text-right">
                {typeNames[mt] || mt}
              </div>
              {data.symbols.map((sym) => {
                const val = getValue(mt, sym);
                return (
                  <div
                    key={sym}
                    className={`w-20 h-12 flex items-center justify-center text-xs font-medium ${getColor(val)} text-white`}
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
  );
}

// ==================== 最佳模型 ====================

function BestModels({ models }: { models: BacktestResult[] }) {
  if (models.length === 0) return null;

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">Top 5 最佳模型（按 Sharpe）</h3>
      <div className="space-y-3">
        {models.map((m, i) => (
          <div key={m.model_id} className="flex items-center justify-between p-3 rounded-clay-sm bg-dark-800/50">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                i === 0 ? "bg-yellow-400/20 text-yellow-400" :
                i === 1 ? "bg-slate-300/20 text-slate-300" :
                i === 2 ? "bg-orange-400/20 text-orange-400" :
                "bg-dark-700 text-slate-400"
              }`}>
                {i + 1}
              </div>
              <div>
                <div className="font-medium text-slate-200">
                  {m.model_type.toUpperCase()} - {m.symbol}
                </div>
                <div className="text-xs text-slate-500">
                  收益 {m.total_return != null ? `${(m.total_return * 100).toFixed(1)}%` : "N/A"}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-neon-blue font-bold">
                Sharpe {m.sharpe_ratio?.toFixed(2) || "N/A"}
              </div>
              <div className="text-xs text-slate-500">
                方向 {m.direction_accuracy != null ? `${(m.direction_accuracy * 100).toFixed(1)}%` : "N/A"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== 主页面 ====================

export default function BacktestPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [summary, setSummary] = useState<BacktestSummary | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [resultsRes, summaryRes, heatmapRes] = await Promise.all([
          api.get<{ items: BacktestResult[]; total: number }>("/backtest/"),
          api.get<BacktestSummary>("/backtest/summary"),
          api.get<HeatmapData>("/backtest/heatmap"),
        ]);
        setResults(resultsRes.items);
        setSummary(summaryRes);
        setHeatmap(heatmapRes);

        const syms = Array.from(new Set(resultsRes.items.map((r) => r.symbol))).sort();
        setSymbols(syms);
      } catch (e: any) {
        setError(e.message || "加载失败");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-neon-blue animate-spin" />
        <span className="ml-3 text-slate-400">加载回测数据...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="clay-card text-center py-12">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={() => window.location.reload()} className="clay-button">重试</button>
      </div>
    );
  }

  // 计算汇总指标
  const avgSharpe = results.length > 0
    ? results.reduce((s, r) => s + (r.sharpe_ratio || 0), 0) / results.length : 0;
  const bestSharpe = results.length > 0
    ? Math.max(...results.map((r) => r.sharpe_ratio || 0)) : 0;
  const avgAccuracy = results.length > 0
    ? results.reduce((s, r) => s + (r.direction_accuracy || 0), 0) / results.length : 0;
  const avgReturn = results.length > 0
    ? results.reduce((s, r) => s + (r.total_return || 0), 0) / results.length : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">回测结果</h1>
          <p className="text-slate-400 text-sm mt-1">
            {results.length} 条回测记录，{symbols.length} 只股票
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock className="w-4 h-4" />
          <span>5 只美股 x 4 种模型</span>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard title="平均夏普比率" value={avgSharpe.toFixed(2)}
          subtitle="所有模型均值" changeType={avgSharpe > 1 ? "up" : "neutral"} icon={Target} delay={0} />
        <SummaryCard title="最佳夏普" value={bestSharpe.toFixed(2)}
          subtitle="单模型最高" changeType="up" icon={TrendingUp} delay={0.1} />
        <SummaryCard title="平均方向准确率" value={`${(avgAccuracy * 100).toFixed(1)}%`}
          subtitle={avgAccuracy > 0.5 ? "高于随机" : "接近随机"} changeType={avgAccuracy > 0.5 ? "up" : "neutral"} icon={Percent} delay={0.2} />
        <SummaryCard title="平均总收益" value={`${(avgReturn * 100).toFixed(1)}%`}
          subtitle="全部模型" changeType={avgReturn > 0 ? "up" : "down"} icon={Activity} delay={0.3} />
      </div>

      {/* 模型类型对比 */}
      {summary && <ModelTypeSummary summary={summary.summary} />}

      {/* Sharpe 热力图 */}
      {heatmap && <SharpeHeatmap data={heatmap} />}

      {/* Top 5 + 回测结果表格 */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div>
          {summary && <BestModels models={summary.best_models} />}
        </div>
        <div className="lg:col-span-2">
          <ResultsTable
            results={results}
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol}
            symbols={symbols}
          />
        </div>
      </div>
    </div>
  );
}
