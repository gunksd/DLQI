"use client";

import { useState } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  TrendingUp,
  Brain,
  Shield,
  Settings,
  BarChart3,
  FileText,
  Menu,
  X,
  ChevronDown,
  Activity,
  Target,
  Layers,
  Database
} from "lucide-react";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: "概览", href: "/dashboard", icon: LayoutDashboard },
  { name: "策略分析", href: "/dashboard/strategies", icon: Target },
  { name: "模型对比", href: "/dashboard/models", icon: Brain },
  { name: "回测结果", href: "/dashboard/backtest", icon: BarChart3 },
  { name: "风险监控", href: "/dashboard/risk", icon: Shield },
  { name: "数据管理", href: "/dashboard/data", icon: Database },
  { name: "参数调优", href: "/dashboard/tuning", icon: Settings },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentPath, setCurrentPath] = useState("/dashboard");

  return (
    <div className="min-h-screen flex">
      {/* 移动端遮罩 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-50
          w-64 bg-dark-900/95 backdrop-blur-md border-r border-dark-700
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-dark-700">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
              DLQI
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 导航菜单 */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = currentPath === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setCurrentPath(item.href)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-clay-sm
                  transition-all duration-200
                  ${
                    isActive
                      ? "bg-primary-600/20 text-primary-400 shadow-clay-sm"
                      : "text-slate-400 hover:text-white hover:bg-dark-800"
                  }
                `}
              >
                <item.icon className="w-5 h-5" />
                <span className="text-sm font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* 底部信息 */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-700">
          <div className="glass-panel !p-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
                <Activity className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-sm font-medium text-slate-200">系统状态</div>
                <div className="text-xs text-neon-green">运行正常</div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-dark-700 bg-dark-900/50 backdrop-blur-sm">
          {/* 移动端菜单按钮 */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden text-slate-400 hover:text-white"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* 搜索栏 */}
          <div className="hidden md:flex items-center flex-1 max-w-md">
            <input
              type="text"
              placeholder="搜索..."
              className="clay-input !py-2 text-sm"
            />
          </div>

          {/* 右侧操作 */}
          <div className="flex items-center gap-4">
            <button className="clay-button-secondary !px-3 !py-2 text-sm">
              <FileText className="w-4 h-4" />
            </button>
            <Link href="/dashboard" className="clay-button !px-4 !py-2 text-sm">
              运行回测
            </Link>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="flex-1 p-4 md:p-6 overflow-auto custom-scrollbar">
          {children}
        </main>
      </div>
    </div>
  );
}
