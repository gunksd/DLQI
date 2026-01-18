"use client";

import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  BarChart3,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Target,
  Zap,
  AlertTriangle
} from "lucide-react";

// 统计卡片组件
function MetricCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
  delay = 0,
}: {
  title: string;
  value: string;
  change?: string;
  changeType?: "up" | "down" | "neutral";
  icon: React.ElementType;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="clay-card"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100">{value}</h3>
          {change && (
            <div
              className={`flex items-center gap-1 mt-2 text-sm ${
                changeType === "up"
                  ? "text-neon-green"
                  : changeType === "down"
                  ? "text-red-400"
                  : "text-slate-400"
              }`}
            >
              {changeType === "up" ? (
                <ArrowUpRight className="w-4 h-4" />
              ) : changeType === "down" ? (
                <ArrowDownRight className="w-4 h-4" />
              ) : null}
              <span>{change}</span>
            </div>
          )}
        </div>
        <div className="p-3 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20">
          <Icon className="w-6 h-6 text-neon-blue" />
        </div>
      </div>
    </motion.div>
  );
}

// 模拟图表组件
function ChartPlaceholder({
  title,
  height = "h-64",
}: {
  title: string;
  height?: string;
}) {
  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">{title}</h3>
      <div
        className={`${height} bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center`}
      >
        <div className="text-center">
          <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">图表加载中...</p>
        </div>
      </div>
    </div>
  );
}

// 最近交易表格
function RecentTrades() {
  const trades = [
    { id: 1, symbol: "AAPL", action: "买入", price: 185.32, quantity: 100, time: "10:32:15", pnl: "+2.5%" },
    { id: 2, symbol: "GOOGL", action: "卖出", price: 142.18, quantity: 50, time: "10:28:45", pnl: "+1.8%" },
    { id: 3, symbol: "MSFT", action: "买入", price: 378.45, quantity: 80, time: "10:15:22", pnl: "-0.3%" },
    { id: 4, symbol: "NVDA", action: "卖出", price: 485.20, quantity: 30, time: "09:58:10", pnl: "+5.2%" },
    { id: 5, symbol: "TSLA", action: "买入", price: 245.80, quantity: 60, time: "09:45:33", pnl: "+0.8%" },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">最近交易</h3>
        <button className="text-sm text-primary-400 hover:text-primary-300">
          查看全部
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>操作</th>
              <th>价格</th>
              <th>数量</th>
              <th>时间</th>
              <th>盈亏</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td className="font-medium text-slate-200">{trade.symbol}</td>
                <td>
                  <span
                    className={`clay-badge ${
                      trade.action === "买入" ? "clay-badge-success" : "clay-badge-danger"
                    }`}
                  >
                    {trade.action}
                  </span>
                </td>
                <td>${trade.price.toFixed(2)}</td>
                <td>{trade.quantity}</td>
                <td className="text-slate-500">{trade.time}</td>
                <td
                  className={
                    trade.pnl.startsWith("+") ? "text-neon-green" : "text-red-400"
                  }
                >
                  {trade.pnl}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 模型性能概览
function ModelPerformance() {
  const models = [
    { name: "LSTM", accuracy: 68.5, sharpe: 1.42, status: "运行中" },
    { name: "LightGBM", accuracy: 65.2, sharpe: 1.28, status: "运行中" },
    { name: "XGBoost", accuracy: 64.8, sharpe: 1.25, status: "待机" },
    { name: "Ensemble", accuracy: 71.2, sharpe: 1.56, status: "运行中" },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">模型性能</h3>
        <button className="text-sm text-primary-400 hover:text-primary-300">
          详情
        </button>
      </div>
      <div className="space-y-4">
        {models.map((model) => (
          <div key={model.name} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-neon-blue" />
              </div>
              <div>
                <div className="font-medium text-slate-200">{model.name}</div>
                <div className="text-xs text-slate-500">
                  准确率: {model.accuracy}% | 夏普: {model.sharpe}
                </div>
              </div>
            </div>
            <span
              className={`clay-badge ${
                model.status === "运行中" ? "clay-badge-success" : "clay-badge-info"
              }`}
            >
              {model.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// 风险预警
function RiskAlerts() {
  const alerts = [
    { level: "warning", message: "AAPL 仓位接近上限 (18.5%)", time: "5分钟前" },
    { level: "info", message: "LightGBM 模型完成重新训练", time: "15分钟前" },
    { level: "danger", message: "日内回撤达到 2.1%", time: "32分钟前" },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">风险预警</h3>
        <span className="clay-badge clay-badge-warning">3 条</span>
      </div>
      <div className="space-y-3">
        {alerts.map((alert, index) => (
          <div
            key={index}
            className={`flex items-start gap-3 p-3 rounded-clay-sm ${
              alert.level === "danger"
                ? "bg-red-500/10 border border-red-500/20"
                : alert.level === "warning"
                ? "bg-yellow-500/10 border border-yellow-500/20"
                : "bg-neon-blue/10 border border-neon-blue/20"
            }`}
          >
            <AlertTriangle
              className={`w-5 h-5 flex-shrink-0 ${
                alert.level === "danger"
                  ? "text-red-400"
                  : alert.level === "warning"
                  ? "text-yellow-400"
                  : "text-neon-blue"
              }`}
            />
            <div className="flex-1">
              <p className="text-sm text-slate-200">{alert.message}</p>
              <p className="text-xs text-slate-500 mt-1">{alert.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">控制台概览</h1>
          <p className="text-slate-400 text-sm mt-1">
            实时监控策略运行状态和绩效指标
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock className="w-4 h-4" />
          <span>最后更新: 2025-01-18 12:00:00</span>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="总资产"
          value="¥1,185,432"
          change="+18.5% 年化"
          changeType="up"
          icon={DollarSign}
          delay={0}
        />
        <MetricCard
          title="今日盈亏"
          value="+¥3,256"
          change="+0.27%"
          changeType="up"
          icon={TrendingUp}
          delay={0.1}
        />
        <MetricCard
          title="夏普比率"
          value="1.42"
          change="优于基准"
          changeType="up"
          icon={Target}
          delay={0.2}
        />
        <MetricCard
          title="最大回撤"
          value="-12.3%"
          change="在控制范围"
          changeType="neutral"
          icon={Activity}
          delay={0.3}
        />
      </div>

      {/* 图表区域 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <ChartPlaceholder title="收益曲线" height="h-80" />
        <ChartPlaceholder title="仓位分布" height="h-80" />
      </div>

      {/* 数据表格和模型概览 */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentTrades />
        </div>
        <div className="space-y-6">
          <ModelPerformance />
          <RiskAlerts />
        </div>
      </div>
    </div>
  );
}
