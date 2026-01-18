"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  TrendingUp,
  Brain,
  Shield,
  BarChart3,
  Zap,
  Database,
  Github,
  FileText,
  ArrowRight,
  Activity,
  Target,
  Layers
} from "lucide-react";

// 功能卡片组件
function FeatureCard({
  icon: Icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="clay-card group cursor-pointer"
    >
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-clay-sm bg-gradient-to-br from-primary-600/20 to-neon-purple/20 group-hover:shadow-neon-blue/30 transition-shadow">
          <Icon className="w-6 h-6 text-neon-blue" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-2">{title}</h3>
          <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
        </div>
      </div>
    </motion.div>
  );
}

// 统计卡片组件
function StatCard({
  value,
  label,
  trend,
  delay = 0,
}: {
  value: string;
  label: string;
  trend?: "up" | "down";
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay }}
      className="stat-card"
    >
      <div className="value">{value}</div>
      <div className="label">{label}</div>
      {trend && (
        <div className={`mt-2 text-sm ${trend === "up" ? "trend-up" : "trend-down"}`}>
          {trend === "up" ? "↑ 上涨" : "↓ 下跌"}
        </div>
      )}
    </motion.div>
  );
}

// 主页面
export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* 导航栏 */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-panel !rounded-none !p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-clay-sm bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center shadow-neon-blue/30">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
              DLQI
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <Link href="/dashboard" className="text-slate-300 hover:text-white transition">
              控制台
            </Link>
            <Link href="/strategies" className="text-slate-300 hover:text-white transition">
              策略分析
            </Link>
            <Link href="/models" className="text-slate-300 hover:text-white transition">
              模型对比
            </Link>
            <Link href="/risk" className="text-slate-300 hover:text-white transition">
              风险监控
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="clay-button-secondary !px-4 !py-2"
            >
              <Github className="w-4 h-4" />
            </a>
            <Link href="/dashboard" className="clay-button !px-4 !py-2">
              开始使用
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero区域 */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-neon-blue/10 border border-neon-blue/30 text-neon-blue text-sm mb-6">
              <Zap className="w-4 h-4" />
              <span>基于深度学习的智能量化系统</span>
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold mb-6"
          >
            <span className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              机器学习
            </span>
            <br />
            <span className="bg-gradient-to-r from-neon-blue via-neon-purple to-neon-blue bg-clip-text text-transparent text-glow">
              量化交易平台
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-slate-400 max-w-2xl mx-auto mb-10"
          >
            集成 LSTM、Transformer、LightGBM 等先进模型，
            提供完整的策略回测、风险管理和可视化分析功能
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap justify-center gap-4"
          >
            <Link href="/dashboard" className="clay-button flex items-center gap-2">
              <Activity className="w-5 h-5" />
              开始回测
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/about" className="neon-button flex items-center gap-2">
              <FileText className="w-5 h-5" />
              查看论文
            </Link>
          </motion.div>

          {/* 统计数据 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-16">
            <StatCard value="18.5%" label="年化收益率" trend="up" delay={0.4} />
            <StatCard value="1.42" label="夏普比率" delay={0.5} />
            <StatCard value="-12.3%" label="最大回撤" delay={0.6} />
            <StatCard value="56.8%" label="胜率" trend="up" delay={0.7} />
          </div>
        </div>
      </section>

      {/* 功能模块 */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              <span className="bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
                核心功能模块
              </span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              完整的量化交易研究框架，从数据采集到策略回测一站式解决
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={Database}
              title="数据采集"
              description="支持 Tushare、Yahoo Finance 等多数据源，自动清洗和预处理"
              delay={0.1}
            />
            <FeatureCard
              icon={Layers}
              title="特征工程"
              description="60+ 技术指标，30+ 统计特征，智能特征选择与降维"
              delay={0.2}
            />
            <FeatureCard
              icon={Brain}
              title="模型训练"
              description="LSTM、Transformer、LightGBM、XGBoost 多模型集成"
              delay={0.3}
            />
            <FeatureCard
              icon={Target}
              title="策略回测"
              description="完整回测引擎，支持交易成本、滑点模拟，多策略对比"
              delay={0.4}
            />
            <FeatureCard
              icon={Shield}
              title="风险控制"
              description="VaR/CVaR 计算，动态止损，仓位管理，压力测试"
              delay={0.5}
            />
            <FeatureCard
              icon={BarChart3}
              title="可视化分析"
              description="K线图、收益曲线、回撤分析，实时数据展示"
              delay={0.6}
            />
          </div>
        </div>
      </section>

      {/* 技术栈 */}
      <section className="py-20 px-4 bg-dark-900/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">技术栈</h2>
            <p className="text-slate-400">采用现代化技术架构，确保系统高性能和可扩展性</p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* 后端 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
              className="glass-panel"
            >
              <h3 className="text-xl font-semibold text-neon-blue mb-4">后端技术</h3>
              <ul className="space-y-3 text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-blue"></span>
                  FastAPI - 高性能 API 框架
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-blue"></span>
                  PyTorch - 深度学习
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-blue"></span>
                  LightGBM / XGBoost
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-blue"></span>
                  PostgreSQL + Redis
                </li>
              </ul>
            </motion.div>

            {/* 前端 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              viewport={{ once: true }}
              className="glass-panel"
            >
              <h3 className="text-xl font-semibold text-neon-purple mb-4">前端技术</h3>
              <ul className="space-y-3 text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-purple"></span>
                  Next.js 14 - React 框架
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-purple"></span>
                  TailwindCSS - 样式系统
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-purple"></span>
                  ECharts - 金融图表
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-purple"></span>
                  Framer Motion - 动画
                </li>
              </ul>
            </motion.div>

            {/* 量化 */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              viewport={{ once: true }}
              className="glass-panel"
            >
              <h3 className="text-xl font-semibold text-neon-green mb-4">量化工具</h3>
              <ul className="space-y-3 text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-green"></span>
                  Pandas / NumPy
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-green"></span>
                  TA-Lib - 技术指标
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-green"></span>
                  Backtrader - 回测引擎
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-neon-green"></span>
                  Optuna - 超参优化
                </li>
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="clay-card !p-10"
          >
            <h2 className="text-3xl font-bold mb-4">开始你的量化之旅</h2>
            <p className="text-slate-400 mb-8">
              探索数据驱动的交易策略，让机器学习为你的投资决策赋能
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/dashboard" className="clay-button">
                进入控制台
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="clay-button-secondary flex items-center gap-2"
              >
                <Github className="w-5 h-5" />
                GitHub
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="py-8 px-4 border-t border-dark-700">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-neon-blue" />
            <span className="text-slate-400">DLQI - 毕业设计项目 © 2025</span>
          </div>
          <div className="text-slate-500 text-sm">
            基于机器学习的量化交易策略系统设计与实现
          </div>
        </div>
      </footer>
    </main>
  );
}
