"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Target,
  Zap,
  Brain,
  RefreshCw,
  CheckCircle,
} from "lucide-react";
import api from "@/lib/api";

// ==================== 类型定义 ====================

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
  summary: Record<string, {
    count: number;
    avg_sharpe: number | null;
    avg_return: number | null;
    avg_direction_accuracy: number | null;
  }>;
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

// ==================== 统计卡片 ====================

function MetricCard({
  title, value, change, changeType, icon: Icon, delay = 0,
}: {
  title: string; value: string; change?: string;
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
          {change && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              changeType === "up" ? "text-neon-green" : changeType === "down" ? "text-red-400" : "text-slate-400"
            }`}>
              {changeType === "up" ? <ArrowUpRight className="w-4 h-4" /> :
               changeType === "down" ? <ArrowDownRight className="w-4 h-4" /> : null}
              <span>{change}</span>
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

// ==================== 模型性能概览 ====================

function ModelPerformance({ summary }: { summary: BacktestSummary["summary"] }) {
  const types = Object.entries(summary);
  if (types.length === 0) return null;

  const typeNames: Record<string, string> = {
    lstm: "BiLSTM+Attention", transformer: "Transformer",
    lightgbm: "LightGBM", xgboost: "XGBoost",
  };
  const typeColors: Record<string, string> = {
    lstm: "from-blue-600/20 to-cyan-500/20",
    transformer: "from-purple-600/20 to-pink-500/20",
    lightgbm: "from-green-600/20 to-emerald-500/20",
    xgboost: "from-orange-600/20 to-yellow-500/20",
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">模型性能</h3>
      <div className="space-y-4">
        {types.map(([type, stats]) => (
          <div key={type} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-clay-sm bg-gradient-to-br ${typeColors[type] || "from-primary-600/20 to-neon-purple/20"} flex items-center justify-center`}>
                <Zap className="w-5 h-5 text-neon-blue" />
              </div>
              <div>
                <div className="font-medium text-slate-200">{typeNames[type] || type}</div>
                <div className="text-xs text-slate-500">
                  夏普: {stats.avg_sharpe?.toFixed(2) || "N/A"} | 方向准确率: {stats.avg_direction_accuracy != null ? `${(stats.avg_direction_accuracy * 100).toFixed(1)}%` : "N/A"}
                </div>
              </div>
            </div>
            <span className={`clay-badge ${(stats.avg_return || 0) > 0 ? "clay-badge-success" : "clay-badge-danger"}`}>
              {stats.avg_return != null ? `${(stats.avg_return * 100).toFixed(1)}%` : "N/A"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== Top 模型排名 ====================

function TopModels({ models }: { models: BacktestResult[] }) {
  if (models.length === 0) return null;

  const typeNames: Record<string, string> = {
    lstm: "LSTM", transformer: "Transformer",
    lightgbm: "LightGBM", xgboost: "XGBoost",
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">最佳模型 (Sharpe)</h3>
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
                  {typeNames[m.model_type] || m.model_type} - {m.symbol}
                </div>
                <div className="text-xs text-slate-500">
                  收益 {m.total_return != null ? `${(m.total_return * 100).toFixed(1)}%` : "N/A"}
                </div>
              </div>
            </div>
            <div className="text-neon-blue font-bold">
              {m.sharpe_ratio?.toFixed(2) || "N/A"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== 股票覆盖情况 ====================

function SymbolCoverage({ results }: { results: BacktestResult[] }) {
  const bySymbol: Record<string, BacktestResult[]> = {};
  for (const r of results) {
    bySymbol[r.symbol] = bySymbol[r.symbol] || [];
    bySymbol[r.symbol].push(r);
  }

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">股票覆盖</h3>
      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>股票</th>
              <th>模型数</th>
              <th>最佳夏普</th>
              <th>平均准确率</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(bySymbol).sort(([a], [b]) => a.localeCompare(b)).map(([symbol, items]) => {
              const bestSharpe = Math.max(...items.map(r => r.sharpe_ratio || 0));
              const avgAcc = items.reduce((s, r) => s + (r.direction_accuracy || 0), 0) / items.length;
              return (
                <tr key={symbol}>
                  <td className="font-medium text-slate-200">{symbol}</td>
                  <td>{items.length}</td>
                  <td className="text-neon-blue">{bestSharpe.toFixed(2)}</td>
                  <td className="text-yellow-400">{(avgAcc * 100).toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== 主页面 ====================

export default function DashboardPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [summary, setSummary] = useState<BacktestSummary | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [resultsRes, summaryRes, modelsRes] = await Promise.all([
          api.get<{ items: BacktestResult[]; total: number }>("/backtest/"),
          api.get<BacktestSummary>("/backtest/summary"),
          api.get<{ items: ModelInfo[]; total: number }>("/models/"),
        ]);
        setResults(resultsRes.items);
        setSummary(summaryRes);
        setModels(modelsRes.items);
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
        <span className="ml-3 text-slate-400">加载系统数据...</span>
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
    ? Math.max(...results.map(r => r.sharpe_ratio || 0)) : 0;
  const avgAccuracy = results.length > 0
    ? results.reduce((s, r) => s + (r.direction_accuracy || 0), 0) / results.length : 0;
  const avgReturn = results.length > 0
    ? results.reduce((s, r) => s + (r.total_return || 0), 0) / results.length : 0;
  const symbols = new Set(results.map(r => r.symbol));

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">控制台概览</h1>
          <p className="text-slate-400 text-sm mt-1">
            {models.length} 个已训练模型，覆盖 {symbols.size} 只美股
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <CheckCircle className="w-4 h-4 text-neon-green" />
          <span>系统运行正常</span>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="已训练模型" value={`${models.length}`}
          change="5 只股票 x 4 种模型" changeType="neutral"
          icon={Brain} delay={0}
        />
        <MetricCard
          title="平均夏普比率" value={avgSharpe.toFixed(2)}
          change={avgSharpe > 1 ? "优秀" : avgSharpe > 0.5 ? "良好" : "一般"}
          changeType={avgSharpe > 0.5 ? "up" : "neutral"}
          icon={Target} delay={0.1}
        />
        <MetricCard
          title="平均方向准确率" value={`${(avgAccuracy * 100).toFixed(1)}%`}
          change={avgAccuracy > 0.5 ? "高于随机基准" : "接近随机"}
          changeType={avgAccuracy > 0.5 ? "up" : "neutral"}
          icon={Activity} delay={0.2}
        />
        <MetricCard
          title="平均总收益" value={`${(avgReturn * 100).toFixed(1)}%`}
          change={`最佳夏普: ${bestSharpe.toFixed(2)}`}
          changeType={avgReturn > 0 ? "up" : "down"}
          icon={TrendingUp} delay={0.3}
        />
      </div>

      {/* 模型性能 + Top 排名 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {summary && <ModelPerformance summary={summary.summary} />}
        {summary && <TopModels models={summary.best_models} />}
      </div>

      {/* 股票覆盖表 */}
      <SymbolCoverage results={results} />
    </div>
  );
}
