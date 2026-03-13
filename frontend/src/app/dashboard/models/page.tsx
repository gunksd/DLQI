"use client";

import { useState, useEffect } from "react";
import {
  Brain,
  Activity,
  TrendingUp,
  RefreshCw,
  Settings,
  Play,
  CheckCircle,
  Clock,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

interface ModelInfo {
  model_id: string;
  name: string;
  model_type: string;
  model_type_display: string;
  symbol: string;
  status: string;
  val_loss: number | null;
  epochs: number | null;
  features: string[];
  data_points: number | null;
  created_at: string;
}
interface CompareItem {
  model_id: string;
  name: string;
  model_type: string;
  symbol: string;
  val_loss: number | null;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  direction_accuracy: number | null;
  win_rate: number | null;
  excess_return: number | null;
}
interface FeatureItem {
  name: string;
  importance: number;
  rank: number;
}

const fmtPct = (v: number | null) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "N/A";
const TYPE_COLORS: Record<string, string> = {
  lstm: "text-accent-blue",
  transformer: "text-accent-purple",
  lightgbm: "text-gain",
  xgboost: "text-amber-400",
};

function ModelCard({
  model,
  onViewPrediction,
  onSettings,
}: {
  model: ModelInfo;
  onViewPrediction: (m: ModelInfo) => void;
  onSettings: (m: ModelInfo) => void;
}) {
  return (
    <div className="t-card">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-accent-blue/10">
            <Brain
              className={`w-5 h-5 ${TYPE_COLORS[model.model_type] || "text-accent-blue"}`}
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-100">
              {model.symbol}
            </h3>
            <p className="text-xs text-gray-500">{model.model_type_display}</p>
          </div>
        </div>
        <span className="t-badge t-badge-gain flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          已训练
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="p-2 rounded bg-terminal-hover">
          <div className="text-[10px] text-gray-500 mb-0.5">验证损失</div>
          <div className="text-sm font-bold font-num text-gain">
            {model.val_loss ? model.val_loss.toFixed(6) : "N/A"}
          </div>
        </div>
        <div className="p-2 rounded bg-terminal-hover">
          <div className="text-[10px] text-gray-500 mb-0.5">训练轮数</div>
          <div className="text-sm font-bold font-num text-accent-blue">
            {model.epochs || "N/A"}
          </div>
        </div>
        <div className="p-2 rounded bg-terminal-hover">
          <div className="text-[10px] text-gray-500 mb-0.5">特征数</div>
          <div className="text-sm font-bold font-num text-accent-purple">
            {model.features?.length || 0}
          </div>
        </div>
        <div className="p-2 rounded bg-terminal-hover">
          <div className="text-[10px] text-gray-500 mb-0.5">数据量</div>
          <div className="text-sm font-bold font-num text-amber-400">
            {model.data_points || "N/A"}
          </div>
        </div>
      </div>
      <div className="flex items-center text-xs text-gray-500 mb-3 pb-3 border-b border-terminal-border">
        <Clock className="w-3 h-3 mr-1" />
        {model.created_at}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onViewPrediction(model)}
          className="flex-1 t-btn text-xs !py-1.5 flex items-center justify-center gap-1"
        >
          <Play className="w-3.5 h-3.5" />
          查看预测
        </button>
        <button
          onClick={() => onSettings(model)}
          className="t-btn-ghost !px-2.5 !py-1.5"
          title="模型详情"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function PerformanceTable({ data }: { data: CompareItem[] }) {
  if (data.length === 0)
    return (
      <div className="t-card">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">
          模型性能对比
        </h3>
        <p className="text-gray-500 text-center py-8 text-sm">暂无回测数据</p>
      </div>
    );
  return (
    <div className="t-card">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">
        模型性能对比（回测结果）
      </h3>
      <div className="overflow-x-auto">
        <table className="t-table">
          <thead>
            <tr>
              <th>模型</th>
              <th>股票</th>
              <th>年化收益</th>
              <th>夏普比率</th>
              <th>最大回撤</th>
              <th>方向准确率</th>
              <th>超额收益</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <tr key={item.model_id}>
                <td className="font-medium text-gray-200">
                  {item.model_type.toUpperCase()}
                </td>
                <td>{item.symbol}</td>
                <td
                  className={`font-num ${(item.annual_return || 0) >= 0 ? "text-gain" : "text-loss"}`}
                >
                  {fmtPct(item.annual_return)}
                </td>
                <td className="text-accent-blue font-num">
                  {item.sharpe_ratio?.toFixed(2) ?? "N/A"}
                </td>
                <td className="text-loss font-num">
                  {fmtPct(item.max_drawdown)}
                </td>
                <td className="text-amber-400 font-num">
                  {fmtPct(item.direction_accuracy)}
                </td>
                <td
                  className={`font-num ${(item.excess_return || 0) >= 0 ? "text-gain" : "text-loss"}`}
                >
                  {fmtPct(item.excess_return)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FeatureImportance({ features }: { features: FeatureItem[] }) {
  if (features.length === 0) return null;
  const maxImp = Math.max(...features.map((f) => f.importance));
  const colors = [
    "!bg-accent-blue",
    "!bg-accent-purple",
    "!bg-gain",
    "!bg-amber-400",
    "!bg-orange-400",
    "!bg-pink-400",
    "!bg-accent-cyan",
    "!bg-indigo-400",
  ];
  return (
    <div className="t-card">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">特征重要性</h3>
      <div className="space-y-2.5">
        {features.map((f, i) => (
          <div key={f.name}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-300">{f.name}</span>
              <span className="text-gray-400 font-num">
                {(f.importance * 100).toFixed(1)}%
              </span>
            </div>
            <div className="t-progress">
              <div
                className={`t-progress-bar ${colors[i % colors.length]}`}
                style={{ width: `${(f.importance / maxImp) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelStats({ models }: { models: ModelInfo[] }) {
  const types = new Set(models.map((m) => m.model_type));
  const symbols = new Set(models.map((m) => m.symbol));
  const stats = [
    {
      label: "总模型数",
      value: models.length,
      icon: Brain,
      color: "text-accent-blue",
    },
    {
      label: "模型类型",
      value: types.size,
      icon: Activity,
      color: "text-accent-purple",
    },
    {
      label: "覆盖股票",
      value: symbols.size,
      icon: TrendingUp,
      color: "text-gain",
    },
    {
      label: "已训练",
      value: models.filter((m) => m.status === "trained").length,
      icon: CheckCircle,
      color: "text-amber-400",
    },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map((s) => (
        <div key={s.label} className="t-card !p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-accent-blue/10">
              <s.icon className={`w-5 h-5 ${s.color}`} />
            </div>
            <div>
              <div className={`text-xl font-bold font-num ${s.color}`}>
                {s.value}
              </div>
              <div className="text-xs text-gray-500">{s.label}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ModelsPage() {
  const router = useRouter();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [compareData, setCompareData] = useState<CompareItem[]>([]);
  const [features, setFeatures] = useState<FeatureItem[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailModel, setDetailModel] = useState<ModelInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [modelsRes, symbolsRes] = await Promise.all([
          api.get<{ items: ModelInfo[]; total: number }>("/models/"),
          api.get<{ symbols: string[] }>("/models/symbols"),
        ]);
        if (cancelled) return;
        setModels(modelsRes.items);
        setSymbols(symbolsRes.symbols);
        const compareRes = await api.get<{ models: CompareItem[] }>(
          "/models/compare",
        );
        if (cancelled) return;
        setCompareData(compareRes.models);
        const lgb = modelsRes.items.find((m) => m.model_type === "lightgbm");
        if (lgb) {
          try {
            const f = await api.get<{ features: FeatureItem[] }>(
              `/models/${lgb.model_id}/feature-importance`,
            );
            if (!cancelled) setFeatures(f.features);
          } catch {}
        }
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

  const handleViewPrediction = (model: ModelInfo) => {
    // Navigate to strategies page which shows equity curves and predictions
    router.push("/dashboard/strategies");
  };

  const handleSettings = (model: ModelInfo) => {
    setDetailModel(detailModel?.model_id === model.model_id ? null : model);
  };

  const filteredCompare = selectedSymbol
    ? compareData.filter((d) => d.symbol === selectedSymbol)
    : compareData;
  const filteredModels = selectedSymbol
    ? models.filter((m) => m.symbol === selectedSymbol)
    : models;
  const uniqueByType = Array.from(
    new Map(filteredModels.map((m) => [m.model_type, m])).values(),
  );

  if (loading)
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-6 h-6 text-accent-blue animate-spin" />
        <span className="ml-3 text-gray-400 text-sm">加载模型数据...</span>
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
          <h1 className="text-xl font-bold text-gray-100">模型管理</h1>
          <p className="text-gray-500 text-xs mt-1">
            {models.length} 个已训练模型，覆盖 {symbols.length} 只股票
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="t-select !py-1.5 text-xs w-28"
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
          >
            <option value="">全部股票</option>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            onClick={() => window.location.reload()}
            className="t-btn-ghost flex items-center gap-1.5 text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
      </div>

      <ModelStats models={models} />

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {uniqueByType.map((model) => (
          <ModelCard
            key={model.model_id}
            model={model}
            onViewPrediction={handleViewPrediction}
            onSettings={handleSettings}
          />
        ))}
      </div>

      {/* Model detail panel */}
      {detailModel && (
        <div className="t-card !border border-accent-blue/30">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-200">
              模型详情 — {detailModel.model_type_display} / {detailModel.symbol}
            </h3>
            <button
              onClick={() => setDetailModel(null)}
              className="text-gray-500 hover:text-gray-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-2 rounded bg-terminal-hover">
              <div className="text-[10px] text-gray-500">模型ID</div>
              <div className="text-xs text-gray-200 font-mono mt-0.5">
                {detailModel.model_id}
              </div>
            </div>
            <div className="p-2 rounded bg-terminal-hover">
              <div className="text-[10px] text-gray-500">训练时间</div>
              <div className="text-xs text-gray-200 mt-0.5">
                {detailModel.created_at}
              </div>
            </div>
            <div className="p-2 rounded bg-terminal-hover">
              <div className="text-[10px] text-gray-500">数据量</div>
              <div className="text-xs text-gray-200 font-num mt-0.5">
                {detailModel.data_points || "N/A"} 条
              </div>
            </div>
            <div className="p-2 rounded bg-terminal-hover">
              <div className="text-[10px] text-gray-500">状态</div>
              <div className="text-xs text-gain mt-0.5">
                {detailModel.status}
              </div>
            </div>
          </div>
          {detailModel.features.length > 0 && (
            <div className="mt-3 pt-3 border-t border-terminal-border">
              <div className="text-xs text-gray-500 mb-1.5">
                使用特征 ({detailModel.features.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {detailModel.features.map((f) => (
                  <span
                    key={f}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <PerformanceTable data={filteredCompare} />

      <div className="grid lg:grid-cols-2 gap-4">
        <FeatureImportance features={features} />
        <div className="t-card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">全部模型</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto scrollbar-thin">
            {filteredModels.map((model) => (
              <div
                key={model.model_id}
                className="flex items-center justify-between p-2.5 rounded bg-terminal-hover"
              >
                <div className="flex items-center gap-2.5">
                  <CheckCircle className="w-4 h-4 text-gain" />
                  <div>
                    <div className="text-sm font-medium text-gray-200">
                      {model.model_type.toUpperCase()} - {model.symbol}
                    </div>
                    <div className="text-xs text-gray-500">
                      Loss: {model.val_loss?.toFixed(6) || "N/A"}
                    </div>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  {model.model_type_display}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
