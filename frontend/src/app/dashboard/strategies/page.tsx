"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Calendar,
  RefreshCw,
  Download,
  Filter,
  ChevronDown,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Layers,
  Zap
} from "lucide-react";

// 策略卡片
function StrategyCard({
  name,
  description,
  returns,
  sharpe,
  maxDrawdown,
  winRate,
  status,
  delay = 0,
}: {
  name: string;
  description: string;
  returns: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  status: "running" | "stopped" | "backtesting";
  delay?: number;
}) {
  const statusColors = {
    running: "clay-badge-success",
    stopped: "clay-badge-danger",
    backtesting: "clay-badge-warning",
  };

  const statusLabels = {
    running: "运行中",
    stopped: "已停止",
    backtesting: "回测中",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="clay-card"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">{name}</h3>
          <p className="text-sm text-slate-400 mt-1">{description}</p>
        </div>
        <span className={`clay-badge ${statusColors[status]}`}>
          {statusLabels[status]}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">年化收益</div>
          <div className={`text-lg font-bold ${returns >= 0 ? "text-neon-green" : "text-red-400"}`}>
            {returns >= 0 ? "+" : ""}{returns.toFixed(1)}%
          </div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">夏普比率</div>
          <div className="text-lg font-bold text-neon-blue">{sharpe.toFixed(2)}</div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">最大回撤</div>
          <div className="text-lg font-bold text-red-400">{maxDrawdown.toFixed(1)}%</div>
        </div>
        <div className="p-3 rounded-clay-sm bg-dark-800/50">
          <div className="text-xs text-slate-500 mb-1">胜率</div>
          <div className="text-lg font-bold text-neon-purple">{winRate.toFixed(1)}%</div>
        </div>
      </div>

      <div className="flex gap-2">
        <button className="flex-1 clay-button !py-2 text-sm">查看详情</button>
        <button className="clay-button-secondary !px-3 !py-2">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  );
}

// K线图占位
function KLineChart() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">K线图 & 交易信号</h3>
        <div className="flex items-center gap-2">
          <select className="clay-select !py-2 !px-3 text-sm w-32">
            <option>AAPL</option>
            <option>GOOGL</option>
            <option>MSFT</option>
            <option>NVDA</option>
          </select>
          <select className="clay-select !py-2 !px-3 text-sm w-24">
            <option>日K</option>
            <option>周K</option>
            <option>月K</option>
          </select>
        </div>
      </div>

      <div className="h-96 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500">K线图将在此展示</p>
          <p className="text-slate-600 text-sm mt-1">集成 ECharts 实现</p>
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center gap-6 mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-green"></div>
          <span className="text-sm text-slate-400">买入信号</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-400"></div>
          <span className="text-sm text-slate-400">卖出信号</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-blue"></div>
          <span className="text-sm text-slate-400">MA20</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-neon-purple"></div>
          <span className="text-sm text-slate-400">MA60</span>
        </div>
      </div>
    </div>
  );
}

// 收益曲线
function EquityCurve() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">收益曲线对比</h3>
        <div className="flex items-center gap-2">
          <button className="clay-tab active">1月</button>
          <button className="clay-tab">3月</button>
          <button className="clay-tab">6月</button>
          <button className="clay-tab">1年</button>
          <button className="clay-tab">全部</button>
        </div>
      </div>

      <div className="h-64 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">收益曲线图表</p>
        </div>
      </div>

      <div className="flex items-center gap-6 mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 rounded-full bg-neon-blue"></div>
          <span className="text-sm text-slate-400">策略收益</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 rounded-full bg-slate-500"></div>
          <span className="text-sm text-slate-400">基准(沪深300)</span>
        </div>
      </div>
    </div>
  );
}

// 交易记录
function TradeHistory() {
  const trades = [
    { date: "2025-01-18", symbol: "AAPL", action: "买入", price: 185.32, quantity: 100, value: 18532, pnl: null },
    { date: "2025-01-17", symbol: "GOOGL", action: "卖出", price: 142.18, quantity: 50, value: 7109, pnl: "+256.50" },
    { date: "2025-01-16", symbol: "MSFT", action: "买入", price: 378.45, quantity: 30, value: 11353.5, pnl: null },
    { date: "2025-01-15", symbol: "NVDA", action: "卖出", price: 485.20, quantity: 20, value: 9704, pnl: "+1,230.00" },
    { date: "2025-01-14", symbol: "TSLA", action: "买入", price: 245.80, quantity: 40, value: 9832, pnl: null },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">交易记录</h3>
        <div className="flex items-center gap-2">
          <button className="clay-button-secondary !px-3 !py-2 text-sm">
            <Filter className="w-4 h-4" />
          </button>
          <button className="clay-button-secondary !px-3 !py-2 text-sm">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>代码</th>
              <th>操作</th>
              <th>价格</th>
              <th>数量</th>
              <th>金额</th>
              <th>盈亏</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, index) => (
              <tr key={index}>
                <td>{trade.date}</td>
                <td className="font-medium text-slate-200">{trade.symbol}</td>
                <td>
                  <span className={`clay-badge ${trade.action === "买入" ? "clay-badge-success" : "clay-badge-danger"}`}>
                    {trade.action}
                  </span>
                </td>
                <td>${trade.price.toFixed(2)}</td>
                <td>{trade.quantity}</td>
                <td>${trade.value.toLocaleString()}</td>
                <td className={trade.pnl ? (trade.pnl.startsWith("+") ? "text-neon-green" : "text-red-400") : "text-slate-500"}>
                  {trade.pnl || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 技术指标面板
function IndicatorPanel() {
  const indicators = [
    { name: "RSI(14)", value: 58.32, status: "neutral", description: "中性区间" },
    { name: "MACD", value: 1.24, status: "bullish", description: "金叉形态" },
    { name: "布林带", value: "中轨附近", status: "neutral", description: "波动收窄" },
    { name: "ATR(14)", value: 3.45, status: "low", description: "波动较低" },
    { name: "OBV", value: "+15.2M", status: "bullish", description: "量价配合" },
    { name: "KDJ", value: "K:65 D:58", status: "bullish", description: "向上趋势" },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">技术指标</h3>
      <div className="space-y-3">
        {indicators.map((ind) => (
          <div key={ind.name} className="flex items-center justify-between p-3 rounded-clay-sm bg-dark-800/50">
            <div>
              <div className="font-medium text-slate-200">{ind.name}</div>
              <div className="text-xs text-slate-500">{ind.description}</div>
            </div>
            <div className="text-right">
              <div className={`font-bold ${
                ind.status === "bullish" ? "text-neon-green" :
                ind.status === "bearish" ? "text-red-400" : "text-slate-300"
              }`}>
                {ind.value}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StrategiesPage() {
  const strategies = [
    {
      name: "LSTM 趋势跟踪",
      description: "基于LSTM模型的趋势预测策略",
      returns: 18.5,
      sharpe: 1.42,
      maxDrawdown: -12.3,
      winRate: 56.8,
      status: "running" as const,
    },
    {
      name: "LightGBM 多因子",
      description: "机器学习多因子选股策略",
      returns: 15.2,
      sharpe: 1.28,
      maxDrawdown: -10.5,
      winRate: 54.2,
      status: "running" as const,
    },
    {
      name: "动量反转组合",
      description: "技术指标驱动的动量反转策略",
      returns: 12.8,
      sharpe: 1.15,
      maxDrawdown: -8.7,
      winRate: 52.1,
      status: "backtesting" as const,
    },
    {
      name: "模型集成策略",
      description: "LSTM + LightGBM + XGBoost 集成",
      returns: 21.3,
      sharpe: 1.56,
      maxDrawdown: -11.2,
      winRate: 58.5,
      status: "running" as const,
    },
  ];

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">策略分析</h1>
          <p className="text-slate-400 text-sm mt-1">
            查看策略表现、交易信号和技术指标分析
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="clay-button-secondary flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            选择日期
          </button>
          <button className="clay-button flex items-center gap-2">
            <Zap className="w-4 h-4" />
            新建策略
          </button>
        </div>
      </div>

      {/* 策略卡片 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {strategies.map((strategy, index) => (
          <StrategyCard key={strategy.name} {...strategy} delay={index * 0.1} />
        ))}
      </div>

      {/* K线图 */}
      <KLineChart />

      {/* 收益曲线和技术指标 */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <EquityCurve />
        </div>
        <IndicatorPanel />
      </div>

      {/* 交易记录 */}
      <TradeHistory />
    </div>
  );
}
