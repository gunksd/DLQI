"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Calendar,
  Play,
  Pause,
  RefreshCw,
  Download,
  Settings,
  Clock,
  Target,
  Activity,
  DollarSign,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
  Filter
} from "lucide-react";

// 回测汇总卡片
function BacktestSummaryCard({
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
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              changeType === "up" ? "text-neon-green" :
              changeType === "down" ? "text-red-400" : "text-slate-400"
            }`}>
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

// 回测配置面板
function BacktestConfig() {
  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">回测配置</h3>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-slate-400 mb-2">开始日期</label>
          <input
            type="date"
            defaultValue="2023-01-01"
            className="clay-input"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">结束日期</label>
          <input
            type="date"
            defaultValue="2025-01-18"
            className="clay-input"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">初始资金</label>
          <input
            type="number"
            defaultValue="1000000"
            className="clay-input"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">手续费率</label>
          <input
            type="number"
            defaultValue="0.0003"
            step="0.0001"
            className="clay-input"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">策略选择</label>
          <select className="clay-select">
            <option>LSTM 趋势跟踪</option>
            <option>LightGBM 多因子</option>
            <option>模型集成策略</option>
            <option>动量反转组合</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">基准指数</label>
          <select className="clay-select">
            <option>沪深300</option>
            <option>标普500</option>
            <option>纳斯达克100</option>
          </select>
        </div>
      </div>
      <div className="flex gap-3 mt-6">
        <button className="flex-1 clay-button flex items-center justify-center gap-2">
          <Play className="w-4 h-4" />
          运行回测
        </button>
        <button className="clay-button-secondary !px-4">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// 收益曲线图
function EquityCurveChart() {
  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">收益曲线</h3>
        <div className="flex items-center gap-2">
          <button className="clay-tab active">累计收益</button>
          <button className="clay-tab">日收益</button>
          <button className="clay-tab">月收益</button>
        </div>
      </div>
      <div className="h-80 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">收益曲线图表</p>
          <p className="text-slate-600 text-xs mt-1">策略 vs 基准</p>
        </div>
      </div>
      <div className="flex items-center gap-6 mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 rounded-full bg-neon-blue"></div>
          <span className="text-sm text-slate-400">策略收益 +85.2%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 rounded-full bg-slate-500"></div>
          <span className="text-sm text-slate-400">基准收益 +32.5%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 rounded-full bg-neon-green"></div>
          <span className="text-sm text-slate-400">超额收益 +52.7%</span>
        </div>
      </div>
    </div>
  );
}

// 月度收益热力图
function MonthlyReturnsHeatmap() {
  const years = ["2023", "2024", "2025"];
  const months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

  const returns: { [key: string]: number[] } = {
    "2023": [2.3, -1.5, 3.2, 1.8, -0.5, 2.1, 3.5, -2.1, 1.5, 4.2, 2.8, 1.2],
    "2024": [1.5, 2.8, -1.2, 3.5, 2.1, -0.8, 1.8, 3.2, 2.5, -1.5, 2.2, 3.8],
    "2025": [2.5, null, null, null, null, null, null, null, null, null, null, null],
  };

  const getColor = (value: number | null) => {
    if (value === null) return "bg-dark-700";
    if (value >= 3) return "bg-neon-green";
    if (value >= 1) return "bg-neon-green/60";
    if (value >= 0) return "bg-neon-green/30";
    if (value >= -2) return "bg-red-500/50";
    return "bg-red-500";
  };

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">月度收益热力图</h3>
      <div className="overflow-x-auto">
        <div className="inline-block">
          <div className="flex">
            <div className="w-12"></div>
            {months.map((month) => (
              <div key={month} className="w-12 text-center text-xs text-slate-400 py-2">
                {month}
              </div>
            ))}
            <div className="w-16 text-center text-xs text-slate-400 py-2">年度</div>
          </div>
          {years.map((year) => {
            const yearReturns = returns[year].filter((r): r is number => r !== null);
            const yearTotal = yearReturns.reduce((a, b) => a + b, 0);
            return (
              <div key={year} className="flex items-center">
                <div className="w-12 text-xs text-slate-400 pr-2 text-right">{year}</div>
                {returns[year].map((ret, j) => (
                  <div
                    key={j}
                    className={`w-12 h-10 flex items-center justify-center text-xs font-medium ${getColor(ret)} ${
                      ret !== null ? "text-white" : "text-slate-600"
                    }`}
                  >
                    {ret !== null ? `${ret > 0 ? "+" : ""}${ret}%` : "-"}
                  </div>
                ))}
                <div className={`w-16 h-10 flex items-center justify-center text-xs font-bold ${
                  yearTotal >= 0 ? "text-neon-green" : "text-red-400"
                }`}>
                  {yearTotal > 0 ? "+" : ""}{yearTotal.toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// 详细绩效指标
function DetailedMetrics() {
  const metrics = [
    { category: "收益指标", items: [
      { name: "总收益率", value: "85.2%", benchmark: "32.5%" },
      { name: "年化收益率", value: "18.5%", benchmark: "7.2%" },
      { name: "超额收益Alpha", value: "11.3%", benchmark: "-" },
      { name: "月均收益", value: "1.42%", benchmark: "0.58%" },
    ]},
    { category: "风险指标", items: [
      { name: "年化波动率", value: "15.8%", benchmark: "18.2%" },
      { name: "最大回撤", value: "-12.3%", benchmark: "-25.6%" },
      { name: "VaR(95%)", value: "-2.5%", benchmark: "-3.2%" },
      { name: "下行风险", value: "8.5%", benchmark: "12.3%" },
    ]},
    { category: "风险调整指标", items: [
      { name: "夏普比率", value: "1.42", benchmark: "0.58" },
      { name: "索提诺比率", value: "1.85", benchmark: "0.72" },
      { name: "卡玛比率", value: "1.50", benchmark: "0.28" },
      { name: "信息比率", value: "1.25", benchmark: "-" },
    ]},
    { category: "交易指标", items: [
      { name: "总交易次数", value: "1,245", benchmark: "-" },
      { name: "胜率", value: "56.8%", benchmark: "-" },
      { name: "盈亏比", value: "1.52", benchmark: "-" },
      { name: "平均持仓天数", value: "5.2", benchmark: "-" },
    ]},
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">详细绩效指标</h3>
        <button className="clay-button-secondary !px-3 !py-2 text-sm flex items-center gap-1">
          <Download className="w-4 h-4" />
          导出报告
        </button>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        {metrics.map((group) => (
          <div key={group.category}>
            <h4 className="text-sm font-medium text-slate-400 mb-3">{group.category}</h4>
            <div className="space-y-2">
              {group.items.map((item) => (
                <div key={item.name} className="flex items-center justify-between p-2 rounded-clay-sm bg-dark-800/50">
                  <span className="text-slate-300">{item.name}</span>
                  <div className="flex items-center gap-4">
                    <span className="font-medium text-neon-green">{item.value}</span>
                    <span className="text-slate-500 text-sm w-16 text-right">{item.benchmark}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 回撤分析图
function DrawdownChart() {
  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">回撤分析</h3>
      <div className="h-48 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <TrendingDown className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">回撤走势图</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-dark-700">
        <div className="text-center">
          <div className="text-xl font-bold text-red-400">-12.3%</div>
          <div className="text-xs text-slate-500">最大回撤</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-yellow-400">18天</div>
          <div className="text-xs text-slate-500">最长回撤期</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-neon-green">15天</div>
          <div className="text-xs text-slate-500">恢复时间</div>
        </div>
      </div>
    </div>
  );
}

// 交易分布
function TradeDistribution() {
  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">收益分布</h3>
      <div className="h-48 bg-gradient-to-br from-dark-800 to-dark-900 rounded-clay-sm flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">收益分布直方图</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-dark-700">
        <div>
          <div className="text-xs text-slate-500 mb-1">平均盈利</div>
          <div className="text-lg font-bold text-neon-green">+2.35%</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">平均亏损</div>
          <div className="text-lg font-bold text-red-400">-1.55%</div>
        </div>
      </div>
    </div>
  );
}

export default function BacktestPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">回测结果</h1>
          <p className="text-slate-400 text-sm mt-1">
            查看策略回测表现和详细绩效分析
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock className="w-4 h-4" />
          <span>回测周期: 2023-01-01 至 2025-01-18</span>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <BacktestSummaryCard
          title="总收益率"
          value="+85.2%"
          change="超越基准 +52.7%"
          changeType="up"
          icon={TrendingUp}
          delay={0}
        />
        <BacktestSummaryCard
          title="年化收益"
          value="18.5%"
          change="年化复合增长"
          changeType="up"
          icon={Percent}
          delay={0.1}
        />
        <BacktestSummaryCard
          title="夏普比率"
          value="1.42"
          change="风险调整后"
          changeType="up"
          icon={Target}
          delay={0.2}
        />
        <BacktestSummaryCard
          title="最大回撤"
          value="-12.3%"
          change="在控制范围"
          changeType="neutral"
          icon={Activity}
          delay={0.3}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* 回测配置 */}
        <BacktestConfig />

        {/* 收益曲线 */}
        <div className="lg:col-span-2">
          <EquityCurveChart />
        </div>
      </div>

      {/* 月度收益 */}
      <MonthlyReturnsHeatmap />

      {/* 详细指标 */}
      <DetailedMetrics />

      {/* 回撤和分布 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <DrawdownChart />
        <TradeDistribution />
      </div>
    </div>
  );
}
