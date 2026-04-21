// 类型定义 — 与后端 API 响应对齐

export interface BacktestResult {
  id: number;
  model_id: string;
  model_type: string;
  symbol: string;
  total_return: number;
  annual_return: number;
  volatility: number;
  max_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  direction_accuracy: number;
  win_rate: number;
  profit_factor: number;
  n_trades: number;
  total_trades?: number;
  total_commission: number;
  benchmark_return: number;
  excess_return: number;
  status: string;
  created_at?: string;
  composite_score?: number;
  score_breakdown?: {
    sharpe_score: number;
    return_score: number;
    drawdown_score: number;
    accuracy_score: number;
  };
}

export interface ModelInfo {
  model_id: string;
  name: string;
  model_type: string;
  symbol: string;
  val_loss?: number;
  epochs?: number;
  feature_count?: number;
  data_points?: number;
  params?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  model_path?: string;
  status: string;
  created_at?: string;
  // 回测指标（从 metrics 字段展开）
  sharpe_ratio?: number;
  annual_return?: number;
  max_drawdown?: number;
  direction_accuracy?: number;
  win_rate?: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  rank: number;
}

export interface EquityCurve {
  date: string;
  equity: number;
  returns: number;
  drawdown: number;
}

export interface PaperPortfolio {
  id: string;
  name: string;
  initial_capital: number;
  cash: number;
  positions: Record<string, { qty: number; avg_price: number }>;
  total_value: number;
  model_id: string;
  status: string;
  created_at?: string;
}

export interface PaperTrade {
  id: number;
  portfolio_id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  commission: number;
  signal_source?: string;
  timestamp: string;
}

export interface Job {
  id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  current_step: string;
  params?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface RiskOverview {
  portfolio_risk: {
    avg_sharpe: number;
    worst_drawdown: number;
    avg_volatility: number;
    avg_direction_accuracy: number;
    model_count: number;
  };
  var_metrics: {
    var_95: number;
    var_99: number;
    cvar_95: number;
  };
  alerts: RiskAlert[];
}

export interface RiskAlert {
  id: number;
  level: "info" | "warning" | "critical";
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface StockInfo {
  symbol: string;
  name?: string;
  last_date?: string;
  data_points?: number;
}

// 格式化工具
export const fmtPct = (v?: number | null, digits = 2): string => {
  if (v == null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
};

export const fmtNum = (v?: number | null, digits = 4): string => {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(digits);
};

export const fmtMoney = (v?: number | null): string => {
  if (v == null || isNaN(v)) return "—";
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
};
