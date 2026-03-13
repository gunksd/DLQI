/** 回测结果 */
export interface BacktestResult {
  id?: number;
  model_id: string;
  model_type: string;
  symbol: string;
  total_return: number | null;
  annual_return: number | null;
  volatility?: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  sortino_ratio?: number | null;
  calmar_ratio?: number | null;
  direction_accuracy: number | null;
  win_rate: number | null;
  profit_factor?: number | null;
  n_trades: number;
  benchmark_return?: number | null;
  excess_return: number | null;
}

/** 回测汇总 */
export interface BacktestSummary {
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

/** 热力图 */
export interface HeatmapData {
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

/** 模型信息 */
export interface ModelInfo {
  model_id: string;
  name: string;
  model_type: string;
  model_type_display: string;
  symbol: string;
  val_loss: number | null;
  created_at: string;
  n_features?: number;
  data_points?: number;
  epochs?: number;
}

/** 模型对比 */
export interface ModelComparison {
  model_id: string;
  model_type: string;
  symbol: string;
  annual_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  direction_accuracy: number | null;
  win_rate: number | null;
}

/** 特征重要性 */
export interface FeatureImportance {
  feature: string;
  importance: number;
}

/** 模型类型名称映射 */
export const MODEL_TYPE_NAMES: Record<string, string> = {
  lstm: "BiLSTM+Attn",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};

/** 模型类型颜色映射 */
export const MODEL_TYPE_COLORS: Record<string, string> = {
  lstm: "#3B82F6",
  transformer: "#8B5CF6",
  lightgbm: "#10B981",
  xgboost: "#F59E0B",
};

/** 格式化百分比 */
export function fmtPct(v: number | null | undefined, mult = true): string {
  if (v == null) return "-";
  const val = mult ? v * 100 : v;
  return `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`;
}

/** 格式化数字 */
export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null) return "-";
  return v.toFixed(digits);
}
