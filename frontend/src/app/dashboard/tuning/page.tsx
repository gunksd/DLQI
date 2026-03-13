"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  Settings,
  Play,
  RefreshCw,
  Save,
  Upload,
  Download,
  Zap,
  Target,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  X,
  Loader2,
} from "lucide-react";
import { OptimizationProgress as OptimizationChart } from "@/components/charts";
import api from "@/lib/api";

/* ────── Types ────── */
interface BacktestItem {
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
  excess_return: number;
}

/* ────── Toast ────── */
function Toast({
  msg,
  onClose,
}: {
  msg: { text: string; type: "info" | "success" | "error" } | null;
  onClose: () => void;
}) {
  if (!msg) return null;
  const cls =
    msg.type === "success"
      ? "bg-gain/10 text-gain border-gain/20"
      : msg.type === "error"
        ? "bg-loss/10 text-loss border-loss/20"
        : "bg-accent-blue/10 text-accent-blue border-accent-blue/20";
  return (
    <div
      className={`fixed top-4 right-4 z-50 px-4 py-2.5 rounded border text-xs flex items-center gap-2 shadow-lg ${cls}`}
    >
      {msg.type === "success" ? (
        <CheckCircle className="w-3.5 h-3.5" />
      ) : msg.type === "error" ? (
        <XCircle className="w-3.5 h-3.5" />
      ) : (
        <RefreshCw className="w-3.5 h-3.5" />
      )}
      {msg.text}
      <button onClick={onClose} className="ml-2 opacity-60 hover:opacity-100">
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

/* ────── Constants ────── */
const DEFAULTS = {
  learningRate: 0.001,
  hiddenSize: 128,
  numLayers: 2,
  dropout: 0.2,
  batchSize: 32,
  epochs: 100,
  lookbackWindow: 20,
  holdingPeriod: 5,
  stopLoss: 5,
  takeProfit: 10,
  positionSize: 10,
};

const MODEL_LABELS: Record<string, string> = {
  lstm: "LSTM",
  transformer: "Transformer",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
};

/* ────── Sub-components ────── */
function ParameterSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  description,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  description: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="p-3 rounded bg-terminal-hover">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-200">{label}</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-20 px-2 py-1 text-right text-xs bg-terminal-bg border border-terminal-border rounded text-gray-200 font-num"
          />
          {unit && <span className="text-xs text-gray-500">{unit}</span>}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="t-slider w-full"
      />
      <div className="flex items-center justify-between mt-1 text-[10px] text-gray-500">
        <span>
          {min}
          {unit}
        </span>
        <span className="text-gray-400">{description}</span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
}

function ParameterGroup({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className="t-card">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-accent-blue/10">
            <Icon className="w-4 h-4 text-accent-blue" />
          </div>
          <h3 className="text-sm font-semibold text-gray-100">{title}</h3>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {isOpen && <div className="mt-3 space-y-3">{children}</div>}
    </div>
  );
}

function ModelResultCard({
  rank,
  item,
  bestSharpe,
}: {
  rank: number;
  item: BacktestItem;
  bestSharpe: number;
}) {
  const isBest = rank === 1;
  const isGood = rank <= 3;
  const border = isBest
    ? "bg-gain/5 border-gain/20"
    : isGood
      ? "bg-accent-blue/5 border-accent-blue/20"
      : "bg-terminal-hover border-terminal-border";
  const improvement =
    bestSharpe !== 0
      ? ((item.sharpe_ratio / Math.abs(bestSharpe)) * 100 - 100)
      : 0;
  return (
    <div className={`p-3 rounded border ${border}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-200">
          #{rank} {MODEL_LABELS[item.model_type] || item.model_type} - {item.symbol}
        </span>
        {isBest && <span className="t-badge t-badge-gain">最优</span>}
      </div>
      <div className="text-xs text-gray-500 mb-1.5">
        收益率: {(item.total_return * 100).toFixed(1)}% | 最大回撤: {(item.max_drawdown * 100).toFixed(1)}% | 方向准确率: {(item.direction_accuracy * 100).toFixed(1)}%
      </div>
      <div className="flex items-center justify-between">
        <span className={`text-sm font-bold font-num ${isBest ? "text-gain" : "text-gray-200"}`}>
          夏普: {item.sharpe_ratio.toFixed(4)}
        </span>
        {rank > 1 && (
          <span className="text-xs font-num text-loss">
            {improvement.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

function ModelTypeComparison({ items }: { items: BacktestItem[] }) {
  // Average metrics by model type
  const typeStats = useMemo(() => {
    const groups: Record<string, BacktestItem[]> = {};
    for (const item of items) {
      if (!groups[item.model_type]) groups[item.model_type] = [];
      groups[item.model_type].push(item);
    }
    return Object.entries(groups)
      .map(([type, models]) => ({
        type,
        label: MODEL_LABELS[type] || type,
        avgSharpe: models.reduce((s, m) => s + m.sharpe_ratio, 0) / models.length,
        avgReturn: models.reduce((s, m) => s + m.total_return, 0) / models.length,
        avgDrawdown: models.reduce((s, m) => s + m.max_drawdown, 0) / models.length,
        avgAccuracy: models.reduce((s, m) => s + m.direction_accuracy, 0) / models.length,
        count: models.length,
      }))
      .sort((a, b) => b.avgSharpe - a.avgSharpe);
  }, [items]);

  const best = typeStats[0];

  return (
    <div className="t-card">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">模型类型对比（各类型平均值）</h3>
      <table className="t-table">
        <thead>
          <tr>
            <th>模型</th>
            <th>夏普比率</th>
            <th>收益率</th>
            <th>最大回撤</th>
            <th>准确率</th>
          </tr>
        </thead>
        <tbody>
          {typeStats.map((s) => (
            <tr key={s.type}>
              <td className="font-medium text-gray-200">{s.label}</td>
              <td className={`font-num ${s === best ? "text-gain font-bold" : "text-gray-300"}`}>
                {s.avgSharpe.toFixed(3)}
              </td>
              <td className={`font-num ${s.avgReturn >= 0 ? "text-gain" : "text-loss"}`}>
                {(s.avgReturn * 100).toFixed(1)}%
              </td>
              <td className="font-num text-loss">
                {(s.avgDrawdown * 100).toFixed(1)}%
              </td>
              <td className="font-num text-gray-300">
                {(s.avgAccuracy * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface PresetConfig {
  name: string;
  desc: string;
  sharpe: number | null;
  returns: number | null;
  params?: Partial<typeof DEFAULTS>;
}

function PresetConfigs({
  onApply,
  activePreset,
}: {
  onApply: (p: PresetConfig) => void;
  activePreset: string;
}) {
  const presets: PresetConfig[] = [
    {
      name: "保守策略",
      desc: "低风险，稳定收益",
      sharpe: 1.2,
      returns: 12,
      params: {
        learningRate: 0.0005,
        hiddenSize: 64,
        dropout: 0.3,
        batchSize: 64,
        epochs: 50,
        stopLoss: 3,
        takeProfit: 8,
        positionSize: 5,
      },
    },
    {
      name: "平衡策略",
      desc: "风险收益平衡",
      sharpe: 1.4,
      returns: 18,
      params: { ...DEFAULTS },
    },
    {
      name: "激进策略",
      desc: "高风险，高收益",
      sharpe: 1.6,
      returns: 25,
      params: {
        learningRate: 0.002,
        hiddenSize: 256,
        dropout: 0.1,
        batchSize: 16,
        epochs: 200,
        stopLoss: 10,
        takeProfit: 20,
        positionSize: 20,
      },
    },
    { name: "自定义", desc: "自定义参数配置", sharpe: null, returns: null },
  ];
  return (
    <div className="t-card">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">预设配置</h3>
      <div className="grid grid-cols-2 gap-2">
        {presets.map((p) => (
          <button
            key={p.name}
            onClick={() => onApply(p)}
            className={`p-3 rounded transition-colors text-left ${activePreset === p.name ? "bg-accent-blue/10 border border-accent-blue/30" : "bg-terminal-hover hover:bg-terminal-border/50 border border-transparent"}`}
          >
            <div className="text-sm font-medium text-gray-200">{p.name}</div>
            <div className="text-[10px] text-gray-500 mt-0.5">{p.desc}</div>
            {p.sharpe && (
              <div className="flex items-center gap-3 mt-1.5 text-xs">
                <span className="text-accent-blue font-num">
                  夏普: {p.sharpe}
                </span>
                <span className="text-gain font-num">收益: {p.returns}%</span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ────── Main Page ────── */
export default function TuningPage() {
  const [learningRate, setLearningRate] = useState(DEFAULTS.learningRate);
  const [hiddenSize, setHiddenSize] = useState(DEFAULTS.hiddenSize);
  const [numLayers, setNumLayers] = useState(DEFAULTS.numLayers);
  const [dropout, setDropout] = useState(DEFAULTS.dropout);
  const [batchSize, setBatchSize] = useState(DEFAULTS.batchSize);
  const [epochs, setEpochs] = useState(DEFAULTS.epochs);
  const [lookbackWindow, setLookbackWindow] = useState(DEFAULTS.lookbackWindow);
  const [holdingPeriod, setHoldingPeriod] = useState(DEFAULTS.holdingPeriod);
  const [stopLoss, setStopLoss] = useState(DEFAULTS.stopLoss);
  const [takeProfit, setTakeProfit] = useState(DEFAULTS.takeProfit);
  const [positionSize, setPositionSize] = useState(DEFAULTS.positionSize);
  const [activePreset, setActivePreset] = useState("平衡策略");
  const [toast, setToast] = useState<{
    text: string;
    type: "info" | "success" | "error";
  } | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(
    () => () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    },
    [],
  );

  /* ── Real data from backend ── */
  const [backtestItems, setBacktestItems] = useState<BacktestItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ items: BacktestItem[]; total: number }>("/backtest/", { page_size: 50 })
      .then((data) => {
        if (!cancelled) setBacktestItems(data.items);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  // Sort by sharpe descending
  const sorted = useMemo(
    () => [...backtestItems].sort((a, b) => b.sharpe_ratio - a.sharpe_ratio),
    [backtestItems],
  );

  // Build optimization chart data from real results
  const optData = useMemo(() => {
    if (sorted.length === 0) return null;
    const trials: number[] = [];
    const currentValues: number[] = [];
    const bestValues: number[] = [];
    // Show models in order of id (simulating trial order)
    const byId = [...backtestItems].sort((a, b) => a.id - b.id);
    let best = -Infinity;
    for (let i = 0; i < byId.length; i++) {
      trials.push(i + 1);
      currentValues.push(byId[i].sharpe_ratio);
      best = Math.max(best, byId[i].sharpe_ratio);
      bestValues.push(best);
    }
    return { trials, bestValues, currentValues };
  }, [backtestItems, sorted.length]);

  // Summary stats
  const stats = useMemo(() => {
    if (sorted.length === 0) return null;
    const best = sorted[0];
    const positiveCount = sorted.filter((m) => m.sharpe_ratio > 0).length;
    const avgSharpe = sorted.reduce((s, m) => s + m.sharpe_ratio, 0) / sorted.length;
    return {
      total: sorted.length,
      positiveCount,
      bestSharpe: best.sharpe_ratio,
      bestModel: `${MODEL_LABELS[best.model_type] || best.model_type} - ${best.symbol}`,
      avgSharpe,
    };
  }, [sorted]);

  const showToast = useCallback(
    (text: string, type: "info" | "success" | "error" = "info") => {
      setToast({ text, type });
      if (toastTimer.current) clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(() => setToast(null), 4000);
    },
    [],
  );

  const applyPreset = (p: PresetConfig) => {
    setActivePreset(p.name);
    if (p.params) {
      if (p.params.learningRate !== undefined)
        setLearningRate(p.params.learningRate);
      if (p.params.hiddenSize !== undefined) setHiddenSize(p.params.hiddenSize);
      if (p.params.numLayers !== undefined) setNumLayers(p.params.numLayers);
      if (p.params.dropout !== undefined) setDropout(p.params.dropout);
      if (p.params.batchSize !== undefined) setBatchSize(p.params.batchSize);
      if (p.params.epochs !== undefined) setEpochs(p.params.epochs);
      if (p.params.stopLoss !== undefined) setStopLoss(p.params.stopLoss);
      if (p.params.takeProfit !== undefined) setTakeProfit(p.params.takeProfit);
      if (p.params.positionSize !== undefined)
        setPositionSize(p.params.positionSize);
      showToast(`已应用「${p.name}」配置`, "success");
    } else {
      showToast("自定义模式：请手动调整参数", "info");
    }
  };

  const handleReset = () => {
    setLearningRate(DEFAULTS.learningRate);
    setHiddenSize(DEFAULTS.hiddenSize);
    setNumLayers(DEFAULTS.numLayers);
    setDropout(DEFAULTS.dropout);
    setBatchSize(DEFAULTS.batchSize);
    setEpochs(DEFAULTS.epochs);
    setLookbackWindow(DEFAULTS.lookbackWindow);
    setHoldingPeriod(DEFAULTS.holdingPeriod);
    setStopLoss(DEFAULTS.stopLoss);
    setTakeProfit(DEFAULTS.takeProfit);
    setPositionSize(DEFAULTS.positionSize);
    setActivePreset("平衡策略");
    showToast("参数已重置为默认值", "success");
  };

  const handleSave = () => {
    const config = {
      learningRate,
      hiddenSize,
      numLayers,
      dropout,
      batchSize,
      epochs,
      lookbackWindow,
      holdingPeriod,
      stopLoss,
      takeProfit,
      positionSize,
    };
    try {
      localStorage.setItem("dlqi_tuning_config", JSON.stringify(config));
      showToast("配置已保存到本地", "success");
    } catch {
      showToast("保存失败，本地存储不可用", "error");
    }
  };

  const handleExport = () => {
    const config = {
      learningRate,
      hiddenSize,
      numLayers,
      dropout,
      batchSize,
      epochs,
      lookbackWindow,
      holdingPeriod,
      stopLoss,
      takeProfit,
      positionSize,
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tuning_config.json";
    a.click();
    URL.revokeObjectURL(url);
    showToast("配置已导出为 JSON", "success");
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const config = JSON.parse(ev.target?.result as string);
          if (config.learningRate) setLearningRate(config.learningRate);
          if (config.hiddenSize) setHiddenSize(config.hiddenSize);
          if (config.numLayers) setNumLayers(config.numLayers);
          if (config.dropout !== undefined) setDropout(config.dropout);
          if (config.batchSize) setBatchSize(config.batchSize);
          if (config.epochs) setEpochs(config.epochs);
          if (config.lookbackWindow) setLookbackWindow(config.lookbackWindow);
          if (config.holdingPeriod) setHoldingPeriod(config.holdingPeriod);
          if (config.stopLoss) setStopLoss(config.stopLoss);
          if (config.takeProfit) setTakeProfit(config.takeProfit);
          if (config.positionSize) setPositionSize(config.positionSize);
          setActivePreset("自定义");
          showToast("配置已导入", "success");
        } catch {
          showToast("JSON 格式错误", "error");
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleStartOptimization = () => {
    showToast(
      "Optuna 超参数优化需要后端支持，当前展示的是已有模型的真实回测结果",
      "info",
    );
  };

  const handleApplyBest = () => {
    if (!sorted.length) return;
    const best = sorted[0];
    // Apply parameters based on best model type
    if (best.model_type === "lightgbm" || best.model_type === "xgboost") {
      setEpochs(200);
      setLearningRate(0.01);
      setHiddenSize(256);
      setDropout(0);
    } else if (best.model_type === "transformer") {
      setLearningRate(0.0005);
      setHiddenSize(256);
      setNumLayers(3);
      setDropout(0.15);
      setEpochs(150);
    } else {
      setLearningRate(0.0008);
      setHiddenSize(256);
      setNumLayers(2);
      setDropout(0.3);
      setEpochs(100);
    }
    setActivePreset("自定义");
    showToast(
      `已应用最优模型参数（${MODEL_LABELS[best.model_type] || best.model_type} - ${best.symbol}，夏普 ${best.sharpe_ratio.toFixed(3)}）`,
      "success",
    );
  };

  return (
    <div className="space-y-5">
      <Toast msg={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">参数调优</h1>
          <p className="text-gray-500 text-xs mt-1">
            调整模型和策略参数，基于 {backtestItems.length} 个真实回测结果优化
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleImport}
            className="t-btn-ghost flex items-center gap-1.5 text-sm"
          >
            <Upload className="w-4 h-4" />
            导入
          </button>
          <button
            onClick={handleExport}
            className="t-btn-ghost flex items-center gap-1.5 text-sm"
          >
            <Download className="w-4 h-4" />
            导出
          </button>
          <button
            onClick={handleStartOptimization}
            className="t-btn flex items-center gap-1.5 text-sm"
          >
            <Zap className="w-4 h-4" />
            开始优化
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <ParameterGroup title="LSTM 模型参数" icon={Settings}>
            <ParameterSlider label="学习率" value={learningRate} min={0.0001} max={0.01} step={0.0001} description="模型训练速度" onChange={(v) => { setLearningRate(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="隐藏层大小" value={hiddenSize} min={32} max={512} step={32} description="网络容量" onChange={(v) => { setHiddenSize(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="LSTM层数" value={numLayers} min={1} max={4} step={1} unit="层" description="网络深度" onChange={(v) => { setNumLayers(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="Dropout" value={dropout} min={0} max={0.5} step={0.05} description="防止过拟合" onChange={(v) => { setDropout(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="批大小" value={batchSize} min={16} max={128} step={16} description="训练效率" onChange={(v) => { setBatchSize(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="训练轮数" value={epochs} min={10} max={500} step={10} unit="轮" description="训练充分度" onChange={(v) => { setEpochs(v); setActivePreset("自定义"); }} />
          </ParameterGroup>

          <ParameterGroup title="交易策略参数" icon={Target}>
            <ParameterSlider label="回望窗口" value={lookbackWindow} min={5} max={60} step={5} unit="天" description="历史数据长度" onChange={(v) => { setLookbackWindow(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="持仓周期" value={holdingPeriod} min={1} max={20} step={1} unit="天" description="平均持仓时间" onChange={(v) => { setHoldingPeriod(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="止损比例" value={stopLoss} min={1} max={20} step={1} unit="%" description="最大容许亏损" onChange={(v) => { setStopLoss(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="止盈比例" value={takeProfit} min={5} max={50} step={5} unit="%" description="目标收益" onChange={(v) => { setTakeProfit(v); setActivePreset("自定义"); }} />
            <ParameterSlider label="单笔仓位" value={positionSize} min={5} max={25} step={5} unit="%" description="单次交易占比" onChange={(v) => { setPositionSize(v); setActivePreset("自定义"); }} />
          </ParameterGroup>

          {/* Real optimization chart from backtest data */}
          <div className="t-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-200">模型表现趋势</h3>
              <div className="text-xs text-gray-500">
                基于 {backtestItems.length} 个真实回测结果
              </div>
            </div>
            {loading ? (
              <div className="flex items-center justify-center h-[260px] text-gray-500">
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                加载中...
              </div>
            ) : optData ? (
              <OptimizationChart data={optData} height={260} />
            ) : (
              <div className="flex items-center justify-center h-[260px] text-gray-500 text-sm">
                暂无回测数据
              </div>
            )}
            {stats && (
              <div className="grid grid-cols-4 gap-3 mt-3 pt-3 border-t border-terminal-border">
                <div className="text-center">
                  <div className="text-lg font-bold font-num text-gain">{stats.total}</div>
                  <div className="text-[10px] text-gray-500">模型总数</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold font-num text-accent-blue">
                    {stats.positiveCount}
                  </div>
                  <div className="text-[10px] text-gray-500">正夏普模型</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold font-num text-accent-purple">
                    {stats.bestSharpe.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-gray-500">最优夏普</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold font-num text-amber-400">
                    {stats.avgSharpe.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-gray-500">平均夏普</div>
                </div>
              </div>
            )}
          </div>

          <ModelTypeComparison items={backtestItems} />
        </div>

        <div className="space-y-4">
          <PresetConfigs onApply={applyPreset} activePreset={activePreset} />
          <div className="t-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-200">最优模型排名</h3>
              <span className="text-xs text-gray-500">Top 5</span>
            </div>
            {loading ? (
              <div className="flex items-center justify-center py-8 text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                加载中...
              </div>
            ) : (
              <div className="space-y-2">
                {sorted.slice(0, 5).map((item, i) => (
                  <ModelResultCard
                    key={item.model_id}
                    rank={i + 1}
                    item={item}
                    bestSharpe={sorted[0]?.sharpe_ratio ?? 1}
                  />
                ))}
              </div>
            )}
          </div>
          <div className="t-card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">操作</h3>
            <div className="space-y-2">
              <button
                onClick={handleApplyBest}
                className="w-full t-btn flex items-center justify-center gap-1.5 text-sm"
              >
                <Play className="w-4 h-4" />
                应用最优模型参数
              </button>
              <button
                onClick={handleReset}
                className="w-full t-btn-ghost flex items-center justify-center gap-1.5 text-sm"
              >
                <RefreshCw className="w-4 h-4" />
                重置为默认
              </button>
              <button
                onClick={handleSave}
                className="w-full t-btn-ghost flex items-center justify-center gap-1.5 text-sm"
              >
                <Save className="w-4 h-4" />
                保存当前配置
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
