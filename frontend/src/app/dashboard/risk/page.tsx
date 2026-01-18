"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  TrendingDown,
  Activity,
  Target,
  PieChart,
  BarChart3,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  RefreshCw,
  Settings,
  Bell,
  Eye
} from "lucide-react";

// 风险指标卡片
function RiskMetricCard({
  title,
  value,
  threshold,
  status,
  icon: Icon,
  description,
  delay = 0,
}: {
  title: string;
  value: string;
  threshold: string;
  status: "safe" | "warning" | "danger";
  icon: React.ElementType;
  description: string;
  delay?: number;
}) {
  const statusColors = {
    safe: "from-neon-green/20 to-neon-green/5 border-neon-green/30",
    warning: "from-yellow-500/20 to-yellow-500/5 border-yellow-500/30",
    danger: "from-red-500/20 to-red-500/5 border-red-500/30",
  };

  const statusTextColors = {
    safe: "text-neon-green",
    warning: "text-yellow-400",
    danger: "text-red-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`clay-card bg-gradient-to-br ${statusColors[status]} !border`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`p-3 rounded-clay-sm bg-dark-800/50`}>
          <Icon className={`w-6 h-6 ${statusTextColors[status]}`} />
        </div>
        <span className={`clay-badge ${
          status === "safe" ? "clay-badge-success" :
          status === "warning" ? "clay-badge-warning" : "clay-badge-danger"
        }`}>
          {status === "safe" ? "正常" : status === "warning" ? "警告" : "危险"}
        </span>
      </div>
      <div className="mb-2">
        <div className={`text-3xl font-bold ${statusTextColors[status]}`}>{value}</div>
        <div className="text-sm text-slate-400">{title}</div>
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>阈值: {threshold}</span>
        <span>{description}</span>
      </div>
    </motion.div>
  );
}

// VaR 图表占位
function VaRChart() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">VaR 历史走势</h3>
        <div className="flex items-center gap-2">
          <button className="clay-tab active">1周</button>
          <button className="clay-tab">1月</button>
          <button className="clay-tab">3月</button>
        </div>
      </div>
      <div className="h-64 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">VaR 时间序列图表</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-dark-700">
        <div className="text-center">
          <div className="text-xl font-bold text-neon-blue">-2.5%</div>
          <div className="text-xs text-slate-500">VaR (95%)</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-neon-purple">-3.8%</div>
          <div className="text-xs text-slate-500">CVaR (95%)</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-yellow-400">-5.2%</div>
          <div className="text-xs text-slate-500">VaR (99%)</div>
        </div>
      </div>
    </div>
  );
}

// 相关性热力图占位
function CorrelationHeatmap() {
  const assets = ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"];
  const correlations = [
    [1.00, 0.72, 0.68, 0.45, 0.38],
    [0.72, 1.00, 0.75, 0.52, 0.42],
    [0.68, 0.75, 1.00, 0.58, 0.35],
    [0.45, 0.52, 0.58, 1.00, 0.48],
    [0.38, 0.42, 0.35, 0.48, 1.00],
  ];

  const getColor = (value: number) => {
    if (value >= 0.7) return "bg-red-500";
    if (value >= 0.5) return "bg-orange-500";
    if (value >= 0.3) return "bg-yellow-500";
    return "bg-neon-green";
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">资产相关性矩阵</h3>
      <div className="overflow-x-auto">
        <div className="inline-block">
          <div className="flex">
            <div className="w-16"></div>
            {assets.map((asset) => (
              <div key={asset} className="w-14 text-center text-xs text-slate-400 py-2">
                {asset}
              </div>
            ))}
          </div>
          {assets.map((asset, i) => (
            <div key={asset} className="flex items-center">
              <div className="w-16 text-xs text-slate-400 pr-2 text-right">{asset}</div>
              {correlations[i].map((corr, j) => (
                <div
                  key={j}
                  className={`w-14 h-10 flex items-center justify-center text-xs font-medium text-white ${getColor(corr)} ${
                    i === j ? "opacity-50" : ""
                  }`}
                >
                  {corr.toFixed(2)}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-4 mt-4 pt-4 border-t border-dark-700 text-xs text-slate-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-500"></div>
          <span>高相关 (≥0.7)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-yellow-500"></div>
          <span>中相关 (0.3-0.7)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-neon-green"></div>
          <span>低相关 (&lt;0.3)</span>
        </div>
      </div>
    </div>
  );
}

// 仓位分布
function PositionDistribution() {
  const positions = [
    { symbol: "AAPL", weight: 18.5, value: 219432, pnl: "+2.5%", risk: "medium" },
    { symbol: "GOOGL", weight: 15.2, value: 180256, pnl: "+1.8%", risk: "low" },
    { symbol: "MSFT", weight: 14.8, value: 175532, pnl: "-0.3%", risk: "low" },
    { symbol: "NVDA", weight: 12.5, value: 148290, pnl: "+5.2%", risk: "high" },
    { symbol: "TSLA", weight: 10.2, value: 120978, pnl: "+0.8%", risk: "high" },
    { symbol: "现金", weight: 28.8, value: 341944, pnl: "-", risk: "none" },
  ];

  const riskColors = {
    high: "text-red-400",
    medium: "text-yellow-400",
    low: "text-neon-green",
    none: "text-slate-500",
  };

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">仓位分布</h3>
        <span className="clay-badge clay-badge-warning">接近限制</span>
      </div>
      <div className="space-y-3">
        {positions.map((pos) => (
          <div key={pos.symbol} className="flex items-center gap-4">
            <div className="w-16 font-medium text-slate-200">{pos.symbol}</div>
            <div className="flex-1">
              <div className="clay-progress">
                <div
                  className={`clay-progress-bar ${
                    pos.risk === "high" ? "!bg-red-500" :
                    pos.risk === "medium" ? "!bg-yellow-500" : ""
                  }`}
                  style={{ width: `${pos.weight}%` }}
                ></div>
              </div>
            </div>
            <div className="w-16 text-right text-sm text-slate-400">{pos.weight}%</div>
            <div className={`w-16 text-right text-sm ${
              pos.pnl.startsWith("+") ? "text-neon-green" :
              pos.pnl.startsWith("-") ? "text-red-400" : "text-slate-500"
            }`}>
              {pos.pnl}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-dark-700 flex items-center justify-between text-sm">
        <span className="text-slate-400">单股最大仓位限制: 20%</span>
        <span className="text-yellow-400">AAPL 接近上限 (18.5%)</span>
      </div>
    </div>
  );
}

// 风险预警列表
function RiskAlerts() {
  const alerts = [
    {
      level: "danger",
      title: "日内回撤超过阈值",
      description: "当日回撤达到 2.8%，超过 2.5% 预警线",
      time: "10分钟前",
      action: "建议减仓",
    },
    {
      level: "warning",
      title: "AAPL 仓位接近上限",
      description: "当前仓位 18.5%，接近 20% 上限",
      time: "32分钟前",
      action: "暂停加仓",
    },
    {
      level: "warning",
      title: "资产相关性升高",
      description: "科技股板块相关性上升至 0.75",
      time: "1小时前",
      action: "分散投资",
    },
    {
      level: "info",
      title: "VaR 模型已更新",
      description: "使用最新数据重新计算风险价值",
      time: "2小时前",
      action: "查看报告",
    },
  ];

  const levelConfig = {
    danger: { icon: XCircle, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
    warning: { icon: AlertTriangle, color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" },
    info: { icon: AlertCircle, color: "text-neon-blue", bg: "bg-neon-blue/10 border-neon-blue/20" },
  };

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">风险预警</h3>
        <div className="flex items-center gap-2">
          <span className="clay-badge clay-badge-danger">2 条严重</span>
          <button className="clay-button-secondary !px-3 !py-2">
            <Bell className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="space-y-3">
        {alerts.map((alert, index) => {
          const config = levelConfig[alert.level as keyof typeof levelConfig];
          const Icon = config.icon;
          return (
            <div key={index} className={`p-4 rounded-clay-sm border ${config.bg}`}>
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 ${config.color} flex-shrink-0 mt-0.5`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-slate-200">{alert.title}</span>
                    <span className="text-xs text-slate-500">{alert.time}</span>
                  </div>
                  <p className="text-sm text-slate-400 mb-2">{alert.description}</p>
                  <button className="text-sm text-primary-400 hover:text-primary-300">
                    {alert.action} →
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 压力测试结果
function StressTestResults() {
  const scenarios = [
    { name: "2008 金融危机", loss: -35.2, probability: 5, recovery: "18个月" },
    { name: "2020 疫情冲击", loss: -28.5, probability: 10, recovery: "6个月" },
    { name: "利率上升 200bp", loss: -15.8, probability: 20, recovery: "3个月" },
    { name: "科技股回调 20%", loss: -12.3, probability: 25, recovery: "2个月" },
    { name: "温和市场调整", loss: -8.5, probability: 40, recovery: "1个月" },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">压力测试</h3>
        <button className="clay-button-secondary !px-3 !py-2 text-sm flex items-center gap-1">
          <RefreshCw className="w-4 h-4" />
          重新测试
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>情景</th>
              <th>预期损失</th>
              <th>发生概率</th>
              <th>恢复时间</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.name}>
                <td className="font-medium text-slate-200">{scenario.name}</td>
                <td className="text-red-400">{scenario.loss}%</td>
                <td>{scenario.probability}%</td>
                <td className="text-slate-400">{scenario.recovery}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 回撤分析
function DrawdownAnalysis() {
  const drawdowns = [
    { period: "2024-08", maxDrawdown: -8.5, duration: "12天", recovery: "8天" },
    { period: "2024-05", maxDrawdown: -12.3, duration: "18天", recovery: "15天" },
    { period: "2024-02", maxDrawdown: -6.2, duration: "8天", recovery: "5天" },
    { period: "2023-10", maxDrawdown: -9.8, duration: "14天", recovery: "10天" },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">历史回撤分析</h3>
      <div className="h-48 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center mb-4">
        <div className="text-center">
          <TrendingDown className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">回撤走势图</p>
        </div>
      </div>
      <div className="space-y-2">
        {drawdowns.map((dd) => (
          <div key={dd.period} className="flex items-center justify-between p-2 rounded-clay-sm bg-dark-800/50">
            <span className="text-slate-400">{dd.period}</span>
            <span className="text-red-400 font-medium">{dd.maxDrawdown}%</span>
            <span className="text-slate-500 text-sm">持续 {dd.duration}</span>
            <span className="text-neon-green text-sm">恢复 {dd.recovery}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RiskPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">风险监控</h1>
          <p className="text-slate-400 text-sm mt-1">
            实时监控投资组合风险指标和预警信息
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="clay-button-secondary flex items-center gap-2">
            <Settings className="w-4 h-4" />
            风控设置
          </button>
          <button className="clay-button flex items-center gap-2">
            <Eye className="w-4 h-4" />
            实时监控
          </button>
        </div>
      </div>

      {/* 核心风险指标 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <RiskMetricCard
          title="在险价值 VaR(95%)"
          value="-2.5%"
          threshold="-3.0%"
          status="safe"
          icon={Shield}
          description="风险可控"
          delay={0}
        />
        <RiskMetricCard
          title="日内回撤"
          value="-2.8%"
          threshold="-2.5%"
          status="danger"
          icon={TrendingDown}
          description="超过阈值"
          delay={0.1}
        />
        <RiskMetricCard
          title="波动率"
          value="18.5%"
          threshold="25.0%"
          status="safe"
          icon={Activity}
          description="正常范围"
          delay={0.2}
        />
        <RiskMetricCard
          title="Beta 系数"
          value="1.12"
          threshold="1.50"
          status="warning"
          icon={Target}
          description="略高于市场"
          delay={0.3}
        />
      </div>

      {/* VaR图表和相关性矩阵 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <VaRChart />
        <CorrelationHeatmap />
      </div>

      {/* 仓位分布和风险预警 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <PositionDistribution />
        <RiskAlerts />
      </div>

      {/* 压力测试和回撤分析 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <StressTestResults />
        <DrawdownAnalysis />
      </div>
    </div>
  );
}
