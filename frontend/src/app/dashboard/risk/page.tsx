"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Shield,
  TrendingDown,
  Activity,
  Target,
  RefreshCw,
  Settings,
  Eye,
} from "lucide-react";
import {
  VaRChart as VaRChartComponent,
  DrawdownChart,
  HeatmapChart,
} from "@/components/charts";
import api from "@/lib/api";

interface BacktestResult {
  model_id: string;
  model_type: string;
  symbol: string;
  total_return: number | null;
  annual_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  direction_accuracy: number | null;
  n_trades: number;
  excess_return: number | null;
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

interface AnalysisData {
  best_model: {
    model_id: string;
    model_type: string;
    symbol: string;
    sharpe_ratio: number;
    max_drawdown: number;
    volatility?: number;
  };
}

interface CorrData {
  xLabels: string[];
  yLabels: string[];
  values: [number, number, number][];
}

const TYPE_NAMES: Record<string, string> = {
  lstm: "BiLSTM+Attn",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};
const fmtPct = (v: number | null | undefined) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "-";

function RiskMetricCard({
  title,
  value,
  threshold,
  status,
  icon: Icon,
  desc,
}: {
  title: string;
  value: string;
  threshold: string;
  status: "safe" | "warning" | "danger";
  icon: React.ElementType;
  desc: string;
}) {
  const border =
    status === "safe"
      ? "border-gain/30"
      : status === "warning"
        ? "border-amber-400/30"
        : "border-loss/30";
  const text =
    status === "safe"
      ? "text-gain"
      : status === "warning"
        ? "text-amber-400"
        : "text-loss";
  const badge =
    status === "safe"
      ? "t-badge-gain"
      : status === "warning"
        ? "t-badge-warn"
        : "t-badge-loss";
  const label =
    status === "safe" ? "正常" : status === "warning" ? "警告" : "危险";
  return (
    <div className={`t-card !border ${border}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 rounded bg-terminal-hover">
          <Icon className={`w-5 h-5 ${text}`} />
        </div>
        <span className={`t-badge ${badge}`}>{label}</span>
      </div>
      <div className={`text-2xl font-bold font-num ${text}`}>{value}</div>
      <div className="text-xs text-gray-400 mt-0.5">{title}</div>
      <div className="flex items-center justify-between mt-2 text-[10px] text-gray-500">
        <span>阈值: {threshold}</span>
        <span>{desc}</span>
      </div>
    </div>
  );
}

/* Rolling VaR from daily returns */
function computeRollingVaR(returns: number[], window = 30) {
  const var95: number[] = [],
    var99: number[] = [],
    actualLoss: number[] = [];
  for (let i = 0; i < returns.length; i++) {
    const start = Math.max(0, i - window);
    const w = returns.slice(start, i + 1).sort((a, b) => a - b);
    const n = w.length;
    var95.push(w[Math.max(0, Math.floor(n * 0.05))] || 0);
    var99.push(w[Math.max(0, Math.floor(n * 0.01))] || 0);
    actualLoss.push(Math.min(0, returns[i] || 0));
  }
  return { var95, var99, actualLoss };
}

export default function RiskPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [equityCurve, setEquityCurve] = useState<EquityCurveData | null>(null);
  const [corrData, setCorrData] = useState<CorrData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [btRes, analysis, corr] = await Promise.all([
          api.get<{ items: BacktestResult[] }>("/backtest/"),
          api.get<AnalysisData>("/backtest/analysis"),
          api.get<CorrData>("/backtest/correlation"),
        ]);
        if (cancelled) return;
        setResults(btRes.items || []);
        setCorrData(corr);
        if (analysis.best_model?.model_id) {
          const curve = await api.get<EquityCurveData>(
            `/backtest/${analysis.best_model.model_id}/equity-curve`,
          );
          if (cancelled) return;
          setEquityCurve(curve);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || "加载风险数据失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  /* compute risk metrics from real data */
  const riskMetrics = useMemo(() => {
    if (!equityCurve) return null;
    const dr = equityCurve.daily_returns.filter((_, i) => i > 0); // skip initial 0
    const vol =
      Math.sqrt(dr.reduce((s, r) => s + r * r, 0) / dr.length) * Math.sqrt(252);
    const sorted = [...dr].sort((a, b) => a - b);
    const var95 = sorted[Math.floor(sorted.length * 0.05)] || 0;
    const maxDD = Math.min(...equityCurve.drawdown);
    const beta = 1 + (vol - 0.16) / 0.16; // rough beta estimate relative to ~16% market vol
    return { vol, var95, maxDD, beta: Math.max(0.5, Math.min(2.0, beta)) };
  }, [equityCurve]);

  /* drawdown chart data */
  const ddData = useMemo(
    () =>
      equityCurve
        ? {
            dates: equityCurve.dates.map((d) => (d || "").split("T")[0]),
            drawdown: equityCurve.drawdown,
          }
        : null,
    [equityCurve],
  );

  /* VaR chart data */
  const varData = useMemo(() => {
    if (!equityCurve) return null;
    const dr = equityCurve.daily_returns.slice(1); // skip initial 0
    const dates = equityCurve.dates
      .slice(1)
      .map((d) => (d || "").split("T")[0]);
    const { var95, var99, actualLoss } = computeRollingVaR(dr);
    return { dates, var95, var99, actualLoss };
  }, [equityCurve]);

  /* top drawdown events */
  const drawdownEvents = useMemo(() => {
    if (!equityCurve) return [];
    const dd = equityCurve.drawdown;
    const dates = equityCurve.dates;
    const events: { period: string; maxDD: number; dur: number }[] = [];
    let inDD = false,
      ddStart = 0,
      worst = 0;
    for (let i = 0; i < dd.length; i++) {
      if (dd[i] < -0.01 && !inDD) {
        inDD = true;
        ddStart = i;
        worst = dd[i];
      } else if (inDD && dd[i] < worst) {
        worst = dd[i];
      } else if (inDD && dd[i] >= -0.005) {
        events.push({
          period: (dates[ddStart] || "").split("T")[0],
          maxDD: worst,
          dur: i - ddStart,
        });
        inDD = false;
        worst = 0;
      }
    }
    if (inDD)
      events.push({
        period: (dates[ddStart] || "").split("T")[0],
        maxDD: worst,
        dur: dd.length - ddStart,
      });
    return events.sort((a, b) => a.maxDD - b.maxDD).slice(0, 5);
  }, [equityCurve]);

  /* per-symbol risk from backtest results */
  const symbolRisk = useMemo(() => {
    const bestPerSymbol: Record<string, BacktestResult> = {};
    results.forEach((r) => {
      if (
        !bestPerSymbol[r.symbol] ||
        (r.sharpe_ratio || 0) > (bestPerSymbol[r.symbol].sharpe_ratio || 0)
      ) {
        bestPerSymbol[r.symbol] = r;
      }
    });
    return Object.values(bestPerSymbol).sort(
      (a, b) => (b.sharpe_ratio || 0) - (a.sharpe_ratio || 0),
    );
  }, [results]);

  if (loading)
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-6 h-6 text-accent-blue animate-spin" />
        <span className="ml-3 text-gray-400 text-sm">加载风险数据...</span>
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

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">风险监控</h1>
          <p className="text-gray-500 text-xs mt-1">
            基于
            {equityCurve
              ? ` ${TYPE_NAMES[equityCurve.model_type] || equityCurve.model_type}/${equityCurve.symbol} `
              : ""}
            主策略的风险分析
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.location.reload()}
            className="t-btn-ghost flex items-center gap-1.5 text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            刷新数据
          </button>
        </div>
      </div>

      {/* Risk metric cards */}
      {riskMetrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <RiskMetricCard
            title="VaR(95%)"
            value={fmtPct(riskMetrics.var95)}
            threshold="-3.0%"
            status={
              riskMetrics.var95 > -0.03
                ? "safe"
                : riskMetrics.var95 > -0.05
                  ? "warning"
                  : "danger"
            }
            icon={Shield}
            desc={riskMetrics.var95 > -0.03 ? "风险可控" : "需关注"}
          />
          <RiskMetricCard
            title="最大回撤"
            value={fmtPct(riskMetrics.maxDD)}
            threshold="-20.0%"
            status={
              riskMetrics.maxDD > -0.15
                ? "safe"
                : riskMetrics.maxDD > -0.25
                  ? "warning"
                  : "danger"
            }
            icon={TrendingDown}
            desc={riskMetrics.maxDD > -0.15 ? "正常范围" : "超过阈值"}
          />
          <RiskMetricCard
            title="年化波动率"
            value={fmtPct(riskMetrics.vol)}
            threshold="25.0%"
            status={
              riskMetrics.vol < 0.25
                ? "safe"
                : riskMetrics.vol < 0.4
                  ? "warning"
                  : "danger"
            }
            icon={Activity}
            desc={riskMetrics.vol < 0.25 ? "波动正常" : "波动偏高"}
          />
          <RiskMetricCard
            title="Beta 系数"
            value={riskMetrics.beta.toFixed(2)}
            threshold="1.50"
            status={
              riskMetrics.beta < 1.2
                ? "safe"
                : riskMetrics.beta < 1.5
                  ? "warning"
                  : "danger"
            }
            icon={Target}
            desc={riskMetrics.beta < 1.2 ? "低于市场" : "略高于市场"}
          />
        </div>
      )}

      {/* VaR chart + Correlation */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            VaR 历史走势
          </h3>
          {varData ? (
            <VaRChartComponent data={varData} height={280} />
          ) : (
            <div className="h-[280px] flex items-center justify-center text-gray-500 text-sm">
              无数据
            </div>
          )}
        </div>
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">
            资产相关性矩阵
          </h3>
          {corrData && corrData.xLabels.length > 0 ? (
            <HeatmapChart
              data={corrData}
              height={280}
              valueFormatter={(v) => v.toFixed(2)}
            />
          ) : (
            <div className="h-[280px] flex items-center justify-center text-gray-500 text-sm">
              无数据
            </div>
          )}
        </div>
      </div>

      {/* Positions + risk per symbol */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="t-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-200">
              各股票最优策略风险
            </h3>
            <span className="text-xs text-gray-500">
              {symbolRisk.length} 只股票
            </span>
          </div>
          <div className="space-y-2">
            {symbolRisk.map((r) => {
              const risk =
                (r.max_drawdown || 0) < -0.2
                  ? "high"
                  : (r.max_drawdown || 0) < -0.1
                    ? "medium"
                    : "low";
              const retPct = (r.total_return || 0) * 100;
              return (
                <div key={r.symbol} className="flex items-center gap-3">
                  <div className="w-14 text-sm font-medium text-gray-200">
                    {r.symbol}
                  </div>
                  <div className="flex-1">
                    <div className="t-progress">
                      <div
                        className={`t-progress-bar ${risk === "high" ? "!bg-loss" : risk === "medium" ? "!bg-amber-400" : ""}`}
                        style={{
                          width: `${Math.min(100, Math.abs(r.max_drawdown || 0) * 400)}%`,
                        }}
                      />
                    </div>
                  </div>
                  <div className="w-20 text-right text-xs text-gray-400 font-num">
                    DD {fmtPct(r.max_drawdown)}
                  </div>
                  <div
                    className={`w-16 text-right text-xs font-num ${retPct >= 0 ? "text-gain" : "text-loss"}`}
                  >
                    {retPct >= 0 ? "+" : ""}
                    {retPct.toFixed(1)}%
                  </div>
                  <div className="w-16 text-right text-xs text-accent-blue font-num">
                    SR {(r.sharpe_ratio || 0).toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 pt-3 border-t border-terminal-border text-xs text-gray-500">
            <span>
              最优模型类型:{" "}
              {TYPE_NAMES[symbolRisk[0]?.model_type] ||
                symbolRisk[0]?.model_type ||
                "-"}
            </span>
          </div>
        </div>

        {/* Stress test - derived from real data */}
        <div className="t-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-200">
              压力测试 (基于历史数据)
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="t-table">
              <thead>
                <tr>
                  <th>情景</th>
                  <th>预期影响</th>
                  <th>当前防御</th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    name: "市场整体回调 20%",
                    loss: riskMetrics ? riskMetrics.maxDD * 1.5 : -0.3,
                    defense: riskMetrics
                      ? riskMetrics.beta < 1.2
                        ? "低Beta"
                        : "正常Beta"
                      : "-",
                  },
                  {
                    name: "科技股回调 15%",
                    loss: riskMetrics ? riskMetrics.maxDD * 1.2 : -0.2,
                    defense: "集中科技股",
                  },
                  {
                    name: "波动率飙升 2x",
                    loss: riskMetrics ? -riskMetrics.vol * 0.5 : -0.15,
                    defense: riskMetrics
                      ? riskMetrics.vol < 0.3
                        ? "波动可控"
                        : "波动偏高"
                      : "-",
                  },
                  {
                    name: "温和调整 5%",
                    loss: riskMetrics ? riskMetrics.maxDD * 0.5 : -0.05,
                    defense: "策略止损",
                  },
                ].map((s) => (
                  <tr key={s.name}>
                    <td className="text-gray-200">{s.name}</td>
                    <td className="text-loss font-num">
                      {(s.loss * 100).toFixed(1)}%
                    </td>
                    <td className="text-gray-400">{s.defense}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Drawdown chart + events */}
      <div className="t-card">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">
          历史回撤分析
        </h3>
        {ddData ? (
          <DrawdownChart data={ddData} height={200} />
        ) : (
          <div className="h-[200px] flex items-center justify-center text-gray-500 text-sm">
            无数据
          </div>
        )}
        {drawdownEvents.length > 0 && (
          <div className="space-y-1.5 mt-3">
            {drawdownEvents.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded bg-terminal-hover text-xs"
              >
                <span className="text-gray-400">开始 {d.period}</span>
                <span className="text-loss font-num font-medium">
                  {(d.maxDD * 100).toFixed(1)}%
                </span>
                <span className="text-gray-500">持续 {d.dur} 天</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
