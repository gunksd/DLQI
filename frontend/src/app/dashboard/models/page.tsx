"use client";

import { useState } from "react";
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
  Pause,
  CheckCircle,
  XCircle,
  Clock,
  Cpu,
  Database,
  GitBranch
} from "lucide-react";

// 模型卡片
function ModelCard({
  name,
  type,
  accuracy,
  precision,
  recall,
  f1Score,
  trainTime,
  status,
  lastUpdated,
  delay = 0,
}: {
  name: string;
  type: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  trainTime: string;
  status: "trained" | "training" | "pending";
  lastUpdated: string;
  delay?: number;
}) {
  const statusConfig = {
    trained: { color: "clay-badge-success", label: "已训练", icon: CheckCircle },
    training: { color: "clay-badge-warning", label: "训练中", icon: RefreshCw },
    pending: { color: "clay-badge-info", label: "待训练", icon: Clock },
  };

  const StatusIcon = statusConfig[status].icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="clay-card"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20">
            <Brain className="w-6 h-6 text-neon-blue" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">{name}</h3>
            <p className="text-sm text-slate-400">{type}</p>
          </div>
        </div>
        <span className={`clay-badge ${statusConfig[status].color} flex items-center gap-1`}>
          <StatusIcon className={`w-3 h-3 ${status === "training" ? "animate-spin" : ""}`} />
          {statusConfig[status].label}
        </span>
      </div>

      {/* 性能指标 */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">准确率</div>
          <div className="text-xl font-bold text-neon-green">{accuracy.toFixed(1)}%</div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">精确率</div>
          <div className="text-xl font-bold text-neon-blue">{precision.toFixed(1)}%</div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">召回率</div>
          <div className="text-xl font-bold text-neon-purple">{recall.toFixed(1)}%</div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">F1分数</div>
          <div className="text-xl font-bold text-yellow-400">{f1Score.toFixed(1)}%</div>
        </div>
      </div>

      {/* 训练信息 */}
      <div className="flex items-center justify-between text-sm text-slate-400 mb-4 pb-4 border-b border-dark-700">
        <div className="flex items-center gap-1">
          <Clock className="w-4 h-4" />
          训练耗时: {trainTime}
        </div>
        <div>更新: {lastUpdated}</div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button className="flex-1 clay-button !py-2 text-sm flex items-center justify-center gap-1">
          <Play className="w-4 h-4" />
          运行预测
        </button>
        <button className="clay-button-secondary !px-3 !py-2">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  );
}

// 性能对比表格
function PerformanceTable() {
  const models = [
    { name: "LSTM", accuracy: 68.5, precision: 67.2, recall: 69.8, f1: 68.5, sharpe: 1.42, returns: 18.5, drawdown: -12.3 },
    { name: "Transformer", accuracy: 70.2, precision: 69.5, recall: 71.0, f1: 70.2, sharpe: 1.48, returns: 19.8, drawdown: -11.8 },
    { name: "LightGBM", accuracy: 65.2, precision: 64.8, recall: 65.6, f1: 65.2, sharpe: 1.28, returns: 15.2, drawdown: -10.5 },
    { name: "XGBoost", accuracy: 64.8, precision: 64.2, recall: 65.4, f1: 64.8, sharpe: 1.25, returns: 14.8, drawdown: -10.2 },
    { name: "随机森林", accuracy: 62.5, precision: 62.0, recall: 63.0, f1: 62.5, sharpe: 1.18, returns: 12.5, drawdown: -9.5 },
    { name: "集成模型", accuracy: 71.2, precision: 70.5, recall: 71.8, f1: 71.2, sharpe: 1.56, returns: 21.3, drawdown: -11.2 },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">模型性能对比</h3>
        <button className="clay-button-secondary !px-3 !py-2 text-sm flex items-center gap-1">
          <Download className="w-4 h-4" />
          导出报告
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>模型</th>
              <th>准确率</th>
              <th>精确率</th>
              <th>召回率</th>
              <th>F1分数</th>
              <th>夏普比率</th>
              <th>年化收益</th>
              <th>最大回撤</th>
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.name}>
                <td className="font-medium text-slate-200">{model.name}</td>
                <td className="text-neon-green">{model.accuracy}%</td>
                <td>{model.precision}%</td>
                <td>{model.recall}%</td>
                <td>{model.f1}%</td>
                <td className="text-neon-blue">{model.sharpe}</td>
                <td className="text-neon-green">+{model.returns}%</td>
                <td className="text-red-400">{model.drawdown}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ROC曲线占位
function ROCCurve() {
  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">ROC 曲线对比</h3>
      <div className="h-80 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">ROC 曲线将在此展示</p>
          <p className="text-slate-600 text-xs mt-1">各模型AUC值对比</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-blue"></div>
          <span className="text-sm text-slate-400">LSTM (AUC: 0.72)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-purple"></div>
          <span className="text-sm text-slate-400">Transformer (AUC: 0.74)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-green"></div>
          <span className="text-sm text-slate-400">集成模型 (AUC: 0.76)</span>
        </div>
      </div>
    </div>
  );
}

// 混淆矩阵
function ConfusionMatrix() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">混淆矩阵</h3>
        <select className="clay-select !py-2 !px-3 text-sm w-40">
          <option>LSTM</option>
          <option>Transformer</option>
          <option>LightGBM</option>
          <option>集成模型</option>
        </select>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div></div>
        <div className="text-center text-sm text-slate-400 py-2">预测: 涨</div>
        <div className="text-center text-sm text-slate-400 py-2">预测: 跌</div>

        <div className="text-right text-sm text-slate-400 py-4 pr-2">实际: 涨</div>
        <div className="p-4 rounded-clay-sm bg-neon-green/20 text-center">
          <div className="text-2xl font-bold text-neon-green">1,245</div>
          <div className="text-xs text-slate-400 mt-1">TP</div>
        </div>
        <div className="p-4 rounded-clay-sm bg-red-500/20 text-center">
          <div className="text-2xl font-bold text-red-400">312</div>
          <div className="text-xs text-slate-400 mt-1">FN</div>
        </div>

        <div className="text-right text-sm text-slate-400 py-4 pr-2">实际: 跌</div>
        <div className="p-4 rounded-clay-sm bg-red-500/20 text-center">
          <div className="text-2xl font-bold text-red-400">298</div>
          <div className="text-xs text-slate-400 mt-1">FP</div>
        </div>
        <div className="p-4 rounded-clay-sm bg-neon-blue/20 text-center">
          <div className="text-2xl font-bold text-neon-blue">1,145</div>
          <div className="text-xs text-slate-400 mt-1">TN</div>
        </div>
      </div>
    </div>
  );
}

// 特征重要性
function FeatureImportance() {
  const features = [
    { name: "RSI_14", importance: 0.156, color: "bg-neon-blue" },
    { name: "MACD_signal", importance: 0.142, color: "bg-neon-purple" },
    { name: "BB_position", importance: 0.128, color: "bg-neon-green" },
    { name: "volume_ratio", importance: 0.115, color: "bg-yellow-400" },
    { name: "momentum_20", importance: 0.098, color: "bg-orange-400" },
    { name: "volatility_10", importance: 0.085, color: "bg-pink-400" },
    { name: "trend_strength", importance: 0.072, color: "bg-cyan-400" },
    { name: "price_ma_ratio", importance: 0.068, color: "bg-indigo-400" },
  ];

  const maxImportance = Math.max(...features.map(f => f.importance));

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">特征重要性</h3>
      <div className="space-y-3">
        {features.map((feature) => (
          <div key={feature.name}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-slate-300">{feature.name}</span>
              <span className="text-slate-400">{(feature.importance * 100).toFixed(1)}%</span>
            </div>
            <div className="clay-progress">
              <div
                className={`clay-progress-bar ${feature.color}`}
                style={{ width: `${(feature.importance / maxImportance) * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 训练历史
function TrainingHistory() {
  const history = [
    { date: "2025-01-18 10:30", model: "LSTM", accuracy: 68.5, duration: "12分钟", status: "success" },
    { date: "2025-01-17 15:45", model: "Transformer", accuracy: 70.2, duration: "25分钟", status: "success" },
    { date: "2025-01-16 09:20", model: "LightGBM", accuracy: 65.2, duration: "3分钟", status: "success" },
    { date: "2025-01-15 14:00", model: "XGBoost", accuracy: 64.8, duration: "5分钟", status: "success" },
    { date: "2025-01-14 11:30", model: "集成模型", accuracy: 71.2, duration: "35分钟", status: "success" },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">训练历史</h3>
      <div className="space-y-3">
        {history.map((item, index) => (
          <div key={index} className="flex items-center justify-between p-3 rounded-clay-sm bg-dark-800/50">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-neon-green" />
              <div>
                <div className="font-medium text-slate-200">{item.model}</div>
                <div className="text-xs text-slate-500">{item.date}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-neon-green font-medium">{item.accuracy}%</div>
              <div className="text-xs text-slate-500">{item.duration}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ModelsPage() {
  const models = [
    {
      name: "LSTM 网络",
      type: "循环神经网络",
      accuracy: 68.5,
      precision: 67.2,
      recall: 69.8,
      f1Score: 68.5,
      trainTime: "12分钟",
      status: "trained" as const,
      lastUpdated: "今天 10:30",
    },
    {
      name: "Transformer",
      type: "自注意力模型",
      accuracy: 70.2,
      precision: 69.5,
      recall: 71.0,
      f1Score: 70.2,
      trainTime: "25分钟",
      status: "trained" as const,
      lastUpdated: "昨天 15:45",
    },
    {
      name: "LightGBM",
      type: "梯度提升树",
      accuracy: 65.2,
      precision: 64.8,
      recall: 65.6,
      f1Score: 65.2,
      trainTime: "3分钟",
      status: "trained" as const,
      lastUpdated: "2天前",
    },
    {
      name: "XGBoost",
      type: "极端梯度提升",
      accuracy: 64.8,
      precision: 64.2,
      recall: 65.4,
      f1Score: 64.8,
      trainTime: "5分钟",
      status: "training" as const,
      lastUpdated: "训练中...",
    },
  ];

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">模型对比</h1>
          <p className="text-slate-400 text-sm mt-1">
            对比不同机器学习模型的性能和预测效果
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="clay-button-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            重新训练
          </button>
          <button className="clay-button flex items-center gap-2">
            <Zap className="w-4 h-4" />
            新建模型
          </button>
        </div>
      </div>

      {/* 模型卡片 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {models.map((model, index) => (
          <ModelCard key={model.name} {...model} delay={index * 0.1} />
        ))}
      </div>

      {/* 性能对比表格 */}
      <PerformanceTable />

      {/* ROC曲线和混淆矩阵 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <ROCCurve />
        <ConfusionMatrix />
      </div>

      {/* 特征重要性和训练历史 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <FeatureImportance />
        <TrainingHistory />
      </div>
    </div>
  );
}
