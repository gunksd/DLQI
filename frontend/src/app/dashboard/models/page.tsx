"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Zap,
  Activity,
  Target,
  TrendingUp,
  BarChart3,
  RefreshCw,
  Download,
  Settings,
  Play,
  CheckCircle,
  Clock,
} from "lucide-react";
import api from "@/lib/api";

// ==================== 类型定义 ====================

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

// ==================== 模型卡片 ====================

function ModelCard({ model, delay = 0 }: { model: ModelInfo; delay?: number }) {
  const typeColors: Record<string, string> = {
    lstm: "from-blue-600/20 to-cyan-500/20",
    transformer: "from-purple-600/20 to-pink-500/20",
    lightgbm: "from-green-600/20 to-emerald-500/20",
    xgboost: "from-orange-600/20 to-yellow-500/20",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="clay-card"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-clay-sm bg-gradient-to-br ${typeColors[model.model_type] || "from-primary-600/20 to-neon-purple/20"}`}>
            <Brain className="w-6 h-6 text-neon-blue" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">{model.symbol}</h3>
            <p className="text-sm text-slate-400">{model.model_type_display}</p>
          </div>
        </div>
        <span className="clay-badge clay-badge-success flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          已训练
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">验证损失</div>
          <div className="text-xl font-bold text-neon-green">
            {model.val_loss ? model.val_loss.toFixed(6) : "N/A"}
          </div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">训练轮数</div>
          <div className="text-xl font-bold text-neon-blue">
            {model.epochs || "N/A"}
          </div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">特征数</div>
          <div className="text-xl font-bold text-neon-purple">
            {model.features?.length || 0}
          </div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">数据量</div>
          <div className="text-xl font-bold text-yellow-400">
            {model.data_points || "N/A"}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-400 mb-4 pb-4 border-b border-dark-700">
        <div className="flex items-center gap-1">
          <Clock className="w-4 h-4" />
          {model.created_at}
        </div>
      </div>

      <div className="flex gap-2">
        <button className="flex-1 clay-button !py-2 text-sm flex items-center justify-center gap-1">
          <Play className="w-4 h-4" />
          查看预测
        </button>
        <button className="clay-button-secondary !px-3 !py-2">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  );
}

// ==================== 性能对比表格 ====================

function PerformanceTable({ data }: { data: CompareItem[] }) {
  if (data.length === 0) {
    return (
      <div className="clay-card">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">模型性能对比</h3>
        <p className="text-slate-500 text-center py-8">暂无回测数据</p>
      </div>
    );
  }

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">模型性能对比（回测结果）</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="clay-table">
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
                <td className="font-medium text-slate-200">{item.model_type.toUpperCase()}</td>
                <td>{item.symbol}</td>
                <td className={`${(item.annual_return || 0) >= 0 ? "text-neon-green" : "text-red-400"}`}>
                  {item.annual_return != null ? `${(item.annual_return * 100).toFixed(1)}%` : "N/A"}
                </td>
                <td className="text-neon-blue">
                  {item.sharpe_ratio != null ? item.sharpe_ratio.toFixed(2) : "N/A"}
                </td>
                <td className="text-red-400">
                  {item.max_drawdown != null ? `${(item.max_drawdown * 100).toFixed(1)}%` : "N/A"}
                </td>
                <td className="text-yellow-400">
                  {item.direction_accuracy != null ? `${(item.direction_accuracy * 100).toFixed(1)}%` : "N/A"}
                </td>
                <td className={`${(item.excess_return || 0) >= 0 ? "text-neon-green" : "text-red-400"}`}>
                  {item.excess_return != null ? `${(item.excess_return * 100).toFixed(1)}%` : "N/A"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== 特征重要性 ====================

function FeatureImportance({ features }: { features: FeatureItem[] }) {
  if (features.length === 0) return null;

  const maxImportance = Math.max(...features.map((f) => f.importance));
  const colors = [
    "bg-neon-blue", "bg-neon-purple", "bg-neon-green", "bg-yellow-400",
    "bg-orange-400", "bg-pink-400", "bg-cyan-400", "bg-indigo-400",
    "bg-emerald-400", "bg-rose-400", "bg-amber-400", "bg-teal-400",
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">特征重要性</h3>
      <div className="space-y-3">
        {features.map((feature, idx) => (
          <div key={feature.name}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-slate-300">{feature.name}</span>
              <span className="text-slate-400">{(feature.importance * 100).toFixed(1)}%</span>
            </div>
            <div className="clay-progress">
              <div
                className={`clay-progress-bar ${colors[idx % colors.length]}`}
                style={{ width: `${(feature.importance / maxImportance) * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== 模型统计概要 ====================

function ModelStats({ models }: { models: ModelInfo[] }) {
  const types = new Set(models.map((m) => m.model_type));
  const symbols = new Set(models.map((m) => m.symbol));

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[
        { label: "总模型数", value: models.length, icon: Brain, color: "text-neon-blue" },
        { label: "模型类型", value: types.size, icon: Activity, color: "text-neon-purple" },
        { label: "覆盖股票", value: symbols.size, icon: TrendingUp, color: "text-neon-green" },
        { label: "已训练", value: models.filter((m) => m.status === "trained").length, icon: CheckCircle, color: "text-yellow-400" },
      ].map((stat) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="clay-card !p-4"
        >
          <div className="flex items-center gap-3">
            <stat.icon className={`w-8 h-8 ${stat.color}`} />
            <div>
              <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
              <div className="text-xs text-slate-500">{stat.label}</div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ==================== 主页面 ====================

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [compareData, setCompareData] = useState<CompareItem[]>([]);
  const [features, setFeatures] = useState<FeatureItem[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载模型列表
  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [modelsRes, symbolsRes] = await Promise.all([
          api.get<{ items: ModelInfo[]; total: number }>("/models/"),
          api.get<{ symbols: string[] }>("/models/symbols"),
        ]);
        setModels(modelsRes.items);
        setSymbols(symbolsRes.symbols);

        // 加载对比数据
        const compareRes = await api.get<{ models: CompareItem[] }>("/models/compare");
        setCompareData(compareRes.models);

        // 加载第一个 LightGBM 模型的特征重要性（可选，失败不影响页面）
        const lgb = modelsRes.items.find((m) => m.model_type === "lightgbm");
        if (lgb) {
          try {
            const featRes = await api.get<{ features: FeatureItem[] }>(
              `/models/${lgb.model_id}/feature-importance`
            );
            setFeatures(featRes.features);
          } catch {}
        }
      } catch (e: any) {
        setError(e.message || "加载失败");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // 按股票筛选对比数据
  const filteredCompare = selectedSymbol
    ? compareData.filter((d) => d.symbol === selectedSymbol)
    : compareData;

  // 按股票筛选模型卡片（只显示选中股票的最佳模型或全部）
  const filteredModels = selectedSymbol
    ? models.filter((m) => m.symbol === selectedSymbol)
    : models;

  // 按模型类型分组显示（每种类型一个）
  const uniqueByType = Array.from(
    new Map(filteredModels.map((m) => [m.model_type, m])).values()
  );

  const handleRefresh = async () => {
    try {
      await api.get("/models/refresh");
      window.location.reload();
    } catch {}
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-neon-blue animate-spin" />
        <span className="ml-3 text-slate-400">加载模型数据...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="clay-card text-center py-12">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={handleRefresh} className="clay-button">
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">模型管理</h1>
          <p className="text-slate-400 text-sm mt-1">
            {models.length} 个已训练模型，覆盖 {symbols.length} 只股票
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="clay-select !py-2 !px-3 text-sm"
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
          >
            <option value="">全部股票</option>
            {symbols.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button onClick={handleRefresh} className="clay-button-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
      </div>

      {/* 统计概要 */}
      <ModelStats models={models} />

      {/* 模型卡片 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {uniqueByType.map((model, index) => (
          <ModelCard key={model.model_id} model={model} delay={index * 0.1} />
        ))}
      </div>

      {/* 性能对比表格 */}
      <PerformanceTable data={filteredCompare} />

      {/* 特征重要性 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <FeatureImportance features={features} />

        {/* 模型列表 */}
        <div className="clay-card">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">全部模型</h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {filteredModels.map((model) => (
              <div key={model.model_id} className="flex items-center justify-between p-3 rounded-clay-sm bg-dark-800/50">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-neon-green" />
                  <div>
                    <div className="font-medium text-slate-200">
                      {model.model_type.toUpperCase()} - {model.symbol}
                    </div>
                    <div className="text-xs text-slate-500">
                      Loss: {model.val_loss?.toFixed(6) || "N/A"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">{model.model_type_display}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
