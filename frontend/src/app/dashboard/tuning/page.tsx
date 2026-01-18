"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Settings,
  Sliders,
  Play,
  Pause,
  RefreshCw,
  Save,
  Upload,
  Download,
  Zap,
  Activity,
  Target,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight
} from "lucide-react";

// 滑块参数组件
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
  onChange: (value: number) => void;
}) {
  return (
    <div className="p-4 rounded-clay-sm bg-dark-800/50">
      <div className="flex items-center justify-between mb-2">
        <label className="font-medium text-slate-200">{label}</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-20 px-2 py-1 text-right text-sm bg-dark-900 border border-dark-600 rounded text-slate-200"
          />
          {unit && <span className="text-sm text-slate-400">{unit}</span>}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="clay-slider w-full"
      />
      <div className="flex items-center justify-between mt-1 text-xs text-slate-500">
        <span>{min}{unit}</span>
        <span className="text-slate-400">{description}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

// 参数组
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
    <div className="clay-card">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20">
            <Icon className="w-5 h-5 text-neon-blue" />
          </div>
          <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        </div>
        {isOpen ? (
          <ChevronDown className="w-5 h-5 text-slate-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-slate-400" />
        )}
      </button>
      {isOpen && <div className="mt-4 space-y-4">{children}</div>}
    </div>
  );
}

// 优化结果卡片
function OptimizationResult({
  trialNumber,
  params,
  score,
  improvement,
  status,
}: {
  trialNumber: number;
  params: string;
  score: number;
  improvement: number;
  status: "best" | "good" | "normal";
}) {
  return (
    <div className={`p-4 rounded-clay-sm border ${
      status === "best" ? "bg-neon-green/10 border-neon-green/30" :
      status === "good" ? "bg-neon-blue/10 border-neon-blue/30" :
      "bg-dark-800/50 border-dark-700"
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-slate-200">Trial #{trialNumber}</span>
        {status === "best" && (
          <span className="clay-badge clay-badge-success">最优</span>
        )}
      </div>
      <div className="text-sm text-slate-400 mb-2">{params}</div>
      <div className="flex items-center justify-between">
        <span className={`font-bold ${
          status === "best" ? "text-neon-green" : "text-slate-200"
        }`}>
          Score: {score.toFixed(4)}
        </span>
        <span className={improvement >= 0 ? "text-neon-green" : "text-red-400"}>
          {improvement >= 0 ? "+" : ""}{improvement.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

// 实时结果图表占位
function OptimizationChart() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">优化进度</h3>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock className="w-4 h-4" />
          <span>已运行 5分32秒</span>
        </div>
      </div>
      <div className="h-64 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">优化曲线图表</p>
          <p className="text-slate-600 text-xs mt-1">Optuna 贝叶斯优化</p>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-dark-700">
        <div className="text-center">
          <div className="text-xl font-bold text-neon-green">42</div>
          <div className="text-xs text-slate-500">已完成试验</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-neon-blue">58</div>
          <div className="text-xs text-slate-500">剩余试验</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-neon-purple">1.56</div>
          <div className="text-xs text-slate-500">最优夏普</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-yellow-400">+18.5%</div>
          <div className="text-xs text-slate-500">提升幅度</div>
        </div>
      </div>
    </div>
  );
}

// 参数对比表
function ParameterComparison() {
  const comparisons = [
    { param: "学习率", baseline: "0.001", optimized: "0.0008", change: "-20%" },
    { param: "隐藏层", baseline: "128", optimized: "256", change: "+100%" },
    { param: "Dropout", baseline: "0.2", optimized: "0.35", change: "+75%" },
    { param: "批大小", baseline: "32", optimized: "64", change: "+100%" },
    { param: "窗口大小", baseline: "20", optimized: "30", change: "+50%" },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">参数对比</h3>
      <table className="clay-table">
        <thead>
          <tr>
            <th>参数</th>
            <th>基准值</th>
            <th>优化值</th>
            <th>变化</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((item) => (
            <tr key={item.param}>
              <td className="font-medium text-slate-200">{item.param}</td>
              <td className="text-slate-400">{item.baseline}</td>
              <td className="text-neon-green">{item.optimized}</td>
              <td className={item.change.startsWith("+") ? "text-neon-blue" : "text-yellow-400"}>
                {item.change}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 预设配置
function PresetConfigs() {
  const presets = [
    { name: "保守策略", description: "低风险，稳定收益", sharpe: 1.2, returns: 12 },
    { name: "平衡策略", description: "风险收益平衡", sharpe: 1.4, returns: 18 },
    { name: "激进策略", description: "高风险，高收益", sharpe: 1.6, returns: 25 },
    { name: "自定义", description: "自定义参数配置", sharpe: null, returns: null },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">预设配置</h3>
      <div className="grid grid-cols-2 gap-3">
        {presets.map((preset) => (
          <button
            key={preset.name}
            className="p-4 rounded-clay-sm bg-dark-800/50 hover:bg-dark-700/50 transition-colors text-left"
          >
            <div className="font-medium text-slate-200">{preset.name}</div>
            <div className="text-xs text-slate-500 mt-1">{preset.description}</div>
            {preset.sharpe && (
              <div className="flex items-center gap-4 mt-2 text-sm">
                <span className="text-neon-blue">夏普: {preset.sharpe}</span>
                <span className="text-neon-green">收益: {preset.returns}%</span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function TuningPage() {
  // 模型参数状态
  const [learningRate, setLearningRate] = useState(0.001);
  const [hiddenSize, setHiddenSize] = useState(128);
  const [numLayers, setNumLayers] = useState(2);
  const [dropout, setDropout] = useState(0.2);
  const [batchSize, setBatchSize] = useState(32);
  const [epochs, setEpochs] = useState(100);

  // 策略参数状态
  const [lookbackWindow, setLookbackWindow] = useState(20);
  const [holdingPeriod, setHoldingPeriod] = useState(5);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(10);
  const [positionSize, setPositionSize] = useState(10);

  // 优化结果
  const optimizationResults = [
    { trialNumber: 42, params: "lr=0.0008, hidden=256, dropout=0.35", score: 1.5632, improvement: 18.5, status: "best" as const },
    { trialNumber: 38, params: "lr=0.0009, hidden=256, dropout=0.30", score: 1.5421, improvement: 16.8, status: "good" as const },
    { trialNumber: 35, params: "lr=0.0007, hidden=192, dropout=0.35", score: 1.5215, improvement: 15.2, status: "good" as const },
    { trialNumber: 28, params: "lr=0.0010, hidden=128, dropout=0.25", score: 1.4892, improvement: 12.8, status: "normal" as const },
    { trialNumber: 15, params: "lr=0.0012, hidden=128, dropout=0.20", score: 1.4523, improvement: 10.0, status: "normal" as const },
  ];

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">参数调优</h1>
          <p className="text-slate-400 text-sm mt-1">
            调整模型和策略参数，使用 Optuna 进行超参数优化
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="clay-button-secondary flex items-center gap-2">
            <Upload className="w-4 h-4" />
            导入配置
          </button>
          <button className="clay-button-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            导出配置
          </button>
          <button className="clay-button flex items-center gap-2">
            <Zap className="w-4 h-4" />
            开始优化
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* 左侧：参数设置 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 模型参数 */}
          <ParameterGroup title="LSTM 模型参数" icon={Settings}>
            <ParameterSlider
              label="学习率"
              value={learningRate}
              min={0.0001}
              max={0.01}
              step={0.0001}
              description="模型训练速度"
              onChange={setLearningRate}
            />
            <ParameterSlider
              label="隐藏层大小"
              value={hiddenSize}
              min={32}
              max={512}
              step={32}
              description="网络容量"
              onChange={setHiddenSize}
            />
            <ParameterSlider
              label="LSTM层数"
              value={numLayers}
              min={1}
              max={4}
              step={1}
              unit="层"
              description="网络深度"
              onChange={setNumLayers}
            />
            <ParameterSlider
              label="Dropout"
              value={dropout}
              min={0}
              max={0.5}
              step={0.05}
              description="防止过拟合"
              onChange={setDropout}
            />
            <ParameterSlider
              label="批大小"
              value={batchSize}
              min={16}
              max={128}
              step={16}
              description="训练效率"
              onChange={setBatchSize}
            />
            <ParameterSlider
              label="训练轮数"
              value={epochs}
              min={10}
              max={500}
              step={10}
              unit="轮"
              description="训练充分度"
              onChange={setEpochs}
            />
          </ParameterGroup>

          {/* 策略参数 */}
          <ParameterGroup title="交易策略参数" icon={Target}>
            <ParameterSlider
              label="回望窗口"
              value={lookbackWindow}
              min={5}
              max={60}
              step={5}
              unit="天"
              description="历史数据长度"
              onChange={setLookbackWindow}
            />
            <ParameterSlider
              label="持仓周期"
              value={holdingPeriod}
              min={1}
              max={20}
              step={1}
              unit="天"
              description="平均持仓时间"
              onChange={setHoldingPeriod}
            />
            <ParameterSlider
              label="止损比例"
              value={stopLoss}
              min={1}
              max={20}
              step={1}
              unit="%"
              description="最大容许亏损"
              onChange={setStopLoss}
            />
            <ParameterSlider
              label="止盈比例"
              value={takeProfit}
              min={5}
              max={50}
              step={5}
              unit="%"
              description="目标收益"
              onChange={setTakeProfit}
            />
            <ParameterSlider
              label="单笔仓位"
              value={positionSize}
              min={5}
              max={25}
              step={5}
              unit="%"
              description="单次交易占比"
              onChange={setPositionSize}
            />
          </ParameterGroup>

          {/* 优化进度 */}
          <OptimizationChart />

          {/* 参数对比 */}
          <ParameterComparison />
        </div>

        {/* 右侧：优化结果和预设 */}
        <div className="space-y-6">
          {/* 预设配置 */}
          <PresetConfigs />

          {/* 优化结果 */}
          <div className="clay-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-100">优化结果</h3>
              <span className="text-sm text-slate-400">Top 5</span>
            </div>
            <div className="space-y-3">
              {optimizationResults.map((result) => (
                <OptimizationResult key={result.trialNumber} {...result} />
              ))}
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="clay-card">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">操作</h3>
            <div className="space-y-3">
              <button className="w-full clay-button flex items-center justify-center gap-2">
                <Play className="w-4 h-4" />
                应用最优参数
              </button>
              <button className="w-full clay-button-secondary flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4" />
                重置为默认
              </button>
              <button className="w-full clay-button-secondary flex items-center justify-center gap-2">
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
