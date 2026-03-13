"use client";

import Link from "next/link";
import {
  TrendingUp, Brain, Shield, BarChart3, Zap, Database,
  ArrowRight, Activity, Target, Layers,
} from "lucide-react";

function FeatureCard({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="t-card group hover:border-terminal-border-strong transition-colors">
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded bg-accent-blue/10">
          <Icon className="w-5 h-5 text-accent-blue" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-gray-100 mb-1.5">{title}</h3>
          <p className="text-gray-400 text-sm leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}

function StatCard({ value, label, color = "text-accent-blue" }: { value: string; label: string; color?: string }) {
  return (
    <div className="t-card text-center">
      <div className={`text-2xl font-bold font-num ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen bg-terminal-bg">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-terminal-card/90 backdrop-blur-md border-b border-terminal-border">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-14 px-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-accent-blue flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-100">DLQI</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm">
            <Link href="/dashboard" className="text-gray-400 hover:text-white transition">控制台</Link>
            <Link href="/dashboard/strategies" className="text-gray-400 hover:text-white transition">策略分析</Link>
            <Link href="/dashboard/models" className="text-gray-400 hover:text-white transition">模型对比</Link>
            <Link href="/dashboard/risk" className="text-gray-400 hover:text-white transition">风险监控</Link>
          </div>
          <Link href="/dashboard" className="t-btn text-sm !py-1.5">开始使用</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-28 pb-16 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-blue/10 border border-accent-blue/20 text-accent-blue text-xs mb-6">
            <Zap className="w-3.5 h-3.5" />
            <span>基于深度学习的智能量化系统</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold mb-4 text-gray-100">
            机器学习<br />
            <span className="text-accent-blue">量化交易平台</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8">
            集成 LSTM、Transformer、LightGBM 等先进模型，
            提供完整的策略回测、风险管理和可视化分析功能
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/dashboard" className="t-btn flex items-center gap-2">
              <Activity className="w-4 h-4" /> 开始回测 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/dashboard/strategies" className="t-btn-ghost flex items-center gap-2">
              查看策略
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-14">
            <StatCard value="18.5%" label="年化收益率" color="text-gain" />
            <StatCard value="1.42" label="夏普比率" />
            <StatCard value="-12.3%" label="最大回撤" color="text-loss" />
            <StatCard value="56.8%" label="胜率" color="text-gain" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-bold text-gray-100 mb-3">核心功能模块</h2>
            <p className="text-gray-400 text-sm">完整的量化交易研究框架，从数据采集到策略回测一站式解决</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            <FeatureCard icon={Database} title="数据采集" description="支持 Tushare、Yahoo Finance 等多数据源，自动清洗和预处理" />
            <FeatureCard icon={Layers} title="特征工程" description="60+ 技术指标，30+ 统计特征，智能特征选择与降维" />
            <FeatureCard icon={Brain} title="模型训练" description="LSTM、Transformer、LightGBM、XGBoost 多模型集成" />
            <FeatureCard icon={Target} title="策略回测" description="完整回测引擎，支持交易成本、滑点模拟，多策略对比" />
            <FeatureCard icon={Shield} title="风险控制" description="VaR/CVaR 计算，动态止损，仓位管理，压力测试" />
            <FeatureCard icon={BarChart3} title="可视化分析" description="K线图、收益曲线、回撤分析，实时数据展示" />
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 px-4 bg-terminal-card/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-100 mb-3">技术栈</h2>
            <p className="text-gray-400 text-sm">采用现代化技术架构，确保系统高性能和可扩展性</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { title: "后端技术", color: "text-accent-blue", items: ["FastAPI - 高性能 API 框架", "PyTorch - 深度学习", "LightGBM / XGBoost", "PostgreSQL + Redis"] },
              { title: "前端技术", color: "text-accent-purple", items: ["Next.js 14 - React 框架", "TailwindCSS - 样式系统", "ECharts - 金融图表", "Framer Motion - 动画"] },
              { title: "量化工具", color: "text-gain", items: ["Pandas / NumPy", "TA-Lib - 技术指标", "Backtrader - 回测引擎", "Optuna - 超参优化"] },
            ].map((col) => (
              <div key={col.title} className="t-card">
                <h3 className={`text-lg font-semibold ${col.color} mb-3`}>{col.title}</h3>
                <ul className="space-y-2 text-sm text-gray-300">
                  {col.items.map((item) => (
                    <li key={item} className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${col.color === "text-accent-blue" ? "bg-accent-blue" : col.color === "text-accent-purple" ? "bg-accent-purple" : "bg-gain"}`} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto text-center t-card !py-10">
          <h2 className="text-2xl font-bold text-gray-100 mb-3">开始你的量化之旅</h2>
          <p className="text-gray-400 text-sm mb-6">探索数据驱动的交易策略，让机器学习为你的投资决策赋能</p>
          <Link href="/dashboard" className="t-btn">进入控制台</Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-4 border-t border-terminal-border">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-accent-blue" />
            <span className="text-gray-500 text-sm">DLQI - 毕业设计项目 © 2025</span>
          </div>
          <div className="text-gray-600 text-xs">基于机器学习的量化交易策略系统设计与实现</div>
        </div>
      </footer>
    </main>
  );
}
