"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Award, Brain } from "lucide-react";
import {
  KLineChart as KLineChartComponent,
  EquityCurve as EquityCurveComponent,
} from "@/components/charts";
import api from "@/lib/api";

interface AnalysisData {
  best_model: {
    model_id: string;
    model_type: string;
    symbol: string;
    sharpe_ratio: number;
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    direction_accuracy: number;
    win_rate: number;
    n_trades: number;
    excess_return: number;
    advantages: string[];
    why_best: string;
  };
  rankings: Array<{
    model_id: string;
    model_type: string;
    symbol: string;
    sharpe_ratio: number;
    total_return: number;
    max_drawdown: number;
    direction_accuracy: number;
    n_trades: number;
    excess_return: number;
  }>;
  by_model_type: Record<
    string,
    {
      avg_sharpe: number;
      avg_return: number;
      avg_direction_accuracy: number;
      model_count: number;
    }
  >;
}

interface EquityCurveData {
  model_id: string;
  symbol: string;
  model_type: string;
  dates: string[];
  portfolio_values: number[];
  benchmark_values: number[];
  daily_returns: number[];
  drawdown: number[];
  trades: Array<{ date: string; action: string; price: number; cost: number }>;
}

interface StockRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const TYPE_NAMES: Record<string, string> = {
  lstm: "BiLSTM+Attn",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};
const SYMBOLS = ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"];
const fmtPct = (v: number | null | undefined) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "-";

export default function StrategiesPage() {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurveData | null>(null);
  const [stockRecords, setStockRecords] = useState<StockRecord[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get<AnalysisData>("/backtest/analysis");
        if (cancelled) return;
        setAnalysis(data);
        if (data.best_model?.model_id) {
          const curve = await api.get<EquityCurveData>(
            `/backtest/${data.best_model.model_id}/equity-curve`,
          );
          if (cancelled) return;
          setEquityCurve(curve);
          setSelectedSymbol(data.best_model.symbol);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || "加载策略分析失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedSymbol) return;
    let cancelled = false;
    const params: Record<string, string | number> = { limit: 1500 };
    if (equityCurve && equityCurve.dates.length > 0) {
      params.start_date = equityCurve.dates[0].split("T")[0];
      params.end_date =
        equityCurve.dates[equityCurve.dates.length - 1].split("T")[0];
    }
    api
      .get<{ data: StockRecord[] }>(`/data/stocks/${selectedSymbol}`, params)
      .then((r) => {
        if (!cancelled) setStockRecords(r.data || []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selectedSymbol, equityCurve]);

  const loadEquityCurve = (modelId: string, symbol: string) => {
    api
      .get<EquityCurveData>(`/backtest/${modelId}/equity-curve`)
      .then(setEquityCurve);
    setSelectedSymbol(symbol);
  };

  /* K-line data transform */
  const klineData =
    stockRecords.length > 0
      ? (() => {
          const dates = stockRecords.map((r) => (r.date || "").split("T")[0]);
          const values: [number, number, number, number][] = stockRecords.map(
            (r) => [r.open, r.close, r.low, r.high],
          );
          const volumes = stockRecords.map((r) => r.volume);
          const closes = stockRecords.map((r) => r.close);
          const calcMA = (n: number) =>
            closes.map((_, i) =>
              i >= n - 1
                ? closes.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n
                : closes[i],
            );
          const signals =
            equityCurve && equityCurve.symbol === selectedSymbol
              ? equityCurve.trades.map((t) => ({
                  date: t.date,
                  type:
                    t.action === "buy" ? ("buy" as const) : ("sell" as const),
                  price: t.price,
                }))
              : [];
          return {
            dates,
            values,
            volumes,
            ma5: calcMA(5),
            ma20: calcMA(20),
            ma60: calcMA(60),
            signals,
          };
        })()
      : null;

  /* equity curve data transform */
  const equityChartData = equityCurve
    ? (() => {
        const pv = equityCurve.portfolio_values;
        const bv = equityCurve.benchmark_values;
        const p0 = pv[0] || 1,
          b0 = bv[0] || 1;
        return {
          dates: equityCurve.dates.map((d) => (d || "").split("T")[0]),
          strategy: pv.map((v) => v / p0 - 1),
          benchmark: bv.map((v) => v / b0 - 1),
        };
      })()
    : null;

  if (loading)
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-6 h-6 text-accent-blue animate-spin" />
        <span className="ml-3 text-gray-400 text-sm">加载策略分析数据...</span>
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

  const best = analysis?.best_model;
  const topModels = (analysis?.rankings || []).slice(0, 4);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">策略分析</h1>
          <p className="text-gray-500 text-xs mt-1">
            模型策略表现、交易信号和最佳策略推荐
          </p>
        </div>
      </div>

      {/* Best strategy highlight */}
      {best && (
        <div className="t-card !border border-accent-blue/30 bg-accent-blue/5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" />
              <div>
                <h3 className="text-sm font-bold text-gray-100">
                  主策略: {TYPE_NAMES[best.model_type] || best.model_type} —{" "}
                  {best.symbol}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  综合评分最高的交易策略
                </p>
              </div>
            </div>
            <span className="t-badge t-badge-gain">推荐</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 mb-3">
            {[
              {
                label: "Sharpe",
                val: best.sharpe_ratio.toFixed(2),
                cls: "text-accent-blue",
              },
              {
                label: "年化收益",
                val: fmtPct(best.annual_return),
                cls: "text-gain",
              },
              {
                label: "最大回撤",
                val: fmtPct(best.max_drawdown),
                cls: "text-loss",
              },
              {
                label: "方向准确率",
                val: fmtPct(best.direction_accuracy),
                cls: "text-amber-400",
              },
              {
                label: "胜率",
                val: fmtPct(best.win_rate),
                cls: "text-accent-purple",
              },
              {
                label: "交易次数",
                val: String(best.n_trades),
                cls: "text-gray-200",
              },
              {
                label: "超额收益",
                val: `${best.excess_return >= 0 ? "+" : ""}${fmtPct(best.excess_return)}`,
                cls: best.excess_return >= 0 ? "text-gain" : "text-loss",
              },
            ].map((m) => (
              <div key={m.label} className="p-2 rounded bg-terminal-hover">
                <div className="text-[10px] text-gray-500 mb-0.5">
                  {m.label}
                </div>
                <div className={`text-sm font-bold font-num ${m.cls}`}>
                  {m.val}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-terminal-border">
            <div className="flex items-start gap-2">
              <Brain className="w-4 h-4 text-accent-blue mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-medium text-gray-300 mb-1">
                  为什么选择此策略
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {best.why_best}
                </p>
                {best.advantages.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {best.advantages.map((a, i) => (
                      <span
                        key={i}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-gain/10 text-gain border border-gain/20"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top strategy cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {topModels.map((s, i) => (
          <div
            key={s.model_id}
            className={`t-card ${i === 0 ? "!border border-amber-400/20" : ""}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-100">
                  {TYPE_NAMES[s.model_type] || s.model_type} — {s.symbol}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">排名 #{i + 1}</p>
              </div>
              {i === 0 && <span className="t-badge t-badge-gain">最佳</span>}
            </div>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="p-2 rounded bg-terminal-hover">
                <div className="text-[10px] text-gray-500 mb-0.5">总收益</div>
                <div
                  className={`text-sm font-bold font-num ${s.total_return >= 0 ? "text-gain" : "text-loss"}`}
                >
                  {fmtPct(s.total_return)}
                </div>
              </div>
              <div className="p-2 rounded bg-terminal-hover">
                <div className="text-[10px] text-gray-500 mb-0.5">夏普比率</div>
                <div className="text-sm font-bold font-num text-accent-blue">
                  {s.sharpe_ratio.toFixed(2)}
                </div>
              </div>
              <div className="p-2 rounded bg-terminal-hover">
                <div className="text-[10px] text-gray-500 mb-0.5">最大回撤</div>
                <div className="text-sm font-bold font-num text-loss">
                  {fmtPct(s.max_drawdown)}
                </div>
              </div>
              <div className="p-2 rounded bg-terminal-hover">
                <div className="text-[10px] text-gray-500 mb-0.5">
                  方向准确率
                </div>
                <div className="text-sm font-bold font-num text-amber-400">
                  {fmtPct(s.direction_accuracy)}
                </div>
              </div>
            </div>
            <button
              className="w-full t-btn-ghost text-xs !py-1.5"
              onClick={() => loadEquityCurve(s.model_id, s.symbol)}
            >
              查看详情
            </button>
          </div>
        ))}
      </div>

      {/* K-Line chart */}
      <div className="t-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-200">
            K线图 & 交易信号
          </h3>
          <select
            className="t-select !py-1.5 text-xs w-24"
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
          >
            {SYMBOLS.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        {klineData ? (
          <KLineChartComponent data={klineData} height={420} />
        ) : (
          <div className="h-[420px] flex items-center justify-center text-gray-500 text-sm">
            加载K线数据...
          </div>
        )}
      </div>

      {/* Equity curve + model type comparison */}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            收益曲线
            {equityCurve
              ? ` — ${TYPE_NAMES[equityCurve.model_type] || equityCurve.model_type} / ${equityCurve.symbol}`
              : ""}
          </h3>
          {equityChartData ? (
            <EquityCurveComponent data={equityChartData} height={280} />
          ) : (
            <div className="h-[280px] flex items-center justify-center text-gray-500 text-sm">
              选择模型查看收益曲线
            </div>
          )}
        </div>
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            模型类型对比
          </h3>
          <div className="space-y-2">
            {analysis &&
              Object.entries(analysis.by_model_type)
                .sort(([, a], [, b]) => b.avg_sharpe - a.avg_sharpe)
                .map(([type, stats]) => (
                  <div key={type} className="p-2.5 rounded bg-terminal-hover">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-200">
                        {TYPE_NAMES[type] || type}
                      </span>
                      <span className="text-xs text-gray-500">
                        {stats.model_count} 模型
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500">Sharpe </span>
                        <span className="text-accent-blue font-num">
                          {stats.avg_sharpe.toFixed(2)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">收益 </span>
                        <span
                          className={`font-num ${stats.avg_return >= 0 ? "text-gain" : "text-loss"}`}
                        >
                          {fmtPct(stats.avg_return)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">准确 </span>
                        <span className="text-amber-400 font-num">
                          {fmtPct(stats.avg_direction_accuracy)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </div>

      {/* Trade history */}
      {equityCurve && equityCurve.trades.length > 0 && (
        <div className="t-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-200">
              交易记录 — {equityCurve.model_type.toUpperCase()} /{" "}
              {equityCurve.symbol}
            </h3>
            <span className="text-xs text-gray-500">
              {equityCurve.trades.length} 笔交易
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="t-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>代码</th>
                  <th>操作</th>
                  <th>价格</th>
                  <th>手续费</th>
                </tr>
              </thead>
              <tbody>
                {equityCurve.trades
                  .slice(-20)
                  .reverse()
                  .map((t, i) => (
                    <tr key={i}>
                      <td>{t.date}</td>
                      <td className="font-medium text-gray-200">
                        {equityCurve.symbol}
                      </td>
                      <td>
                        <span
                          className={`t-badge ${t.action === "buy" ? "t-badge-gain" : "t-badge-loss"}`}
                        >
                          {t.action === "buy" ? "买入" : "卖出"}
                        </span>
                      </td>
                      <td className="font-num">${t.price.toFixed(2)}</td>
                      <td className="font-num text-gray-500">
                        ${t.cost.toFixed(2)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
