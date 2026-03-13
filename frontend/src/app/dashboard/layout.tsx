"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  TrendingUp,
  Brain,
  Shield,
  Settings,
  BarChart3,
  Menu,
  X,
  Activity,
  Target,
  Database,
  RefreshCw,
  CheckCircle,
  XCircle,
} from "lucide-react";
import api from "@/lib/api";

const navigation = [
  { name: "概览", href: "/dashboard", icon: LayoutDashboard },
  { name: "策略分析", href: "/dashboard/strategies", icon: Target },
  { name: "模型对比", href: "/dashboard/models", icon: Brain },
  { name: "回测结果", href: "/dashboard/backtest", icon: BarChart3 },
  { name: "风险监控", href: "/dashboard/risk", icon: Shield },
  { name: "数据管理", href: "/dashboard/data", icon: Database },
  { name: "参数调优", href: "/dashboard/tuning", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState<{
    text: string;
    type: "info" | "success" | "error";
  } | null>(null);
  const dismissTimer = useRef<ReturnType<typeof setTimeout>>();

  const scheduleDismiss = useCallback((ms: number) => {
    if (dismissTimer.current) clearTimeout(dismissTimer.current);
    dismissTimer.current = setTimeout(() => setPipelineMsg(null), ms);
  }, []);

  /* Clean up timer on unmount */
  useEffect(
    () => () => {
      if (dismissTimer.current) clearTimeout(dismissTimer.current);
    },
    [],
  );

  /* Poll pipeline status while running */
  useEffect(() => {
    if (!pipelineRunning) return;
    let cancelled = false;
    const id = setInterval(async () => {
      if (cancelled) return;
      try {
        const st = await api.get<{
          running: boolean;
          progress: string;
          error: string | null;
          last_run: string | null;
        }>("/backtest/status");
        if (cancelled) return;
        if (!st.running) {
          setPipelineRunning(false);
          clearInterval(id);
          if (st.error) {
            setPipelineMsg({
              text: `Pipeline 失败: ${st.error.slice(0, 120)}`,
              type: "error",
            });
          } else {
            setPipelineMsg({
              text: "Pipeline 运行完成，数据已更新",
              type: "success",
            });
          }
          scheduleDismiss(8000);
        }
      } catch {
        /* ignore poll errors */
      }
    }, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pipelineRunning, scheduleDismiss]);

  const handleRunPipeline = useCallback(async () => {
    if (pipelineRunning) return;
    try {
      setPipelineRunning(true);
      setPipelineMsg({
        text: "Pipeline 启动中... 预计需要 2-5 分钟",
        type: "info",
      });
      await api.post("/backtest/run", {});
    } catch (e: any) {
      setPipelineRunning(false);
      const msg = e?.message || "启动失败";
      setPipelineMsg({
        text: msg.includes("409") ? "Pipeline 正在运行中" : `启动失败: ${msg}`,
        type: "error",
      });
      scheduleDismiss(5000);
    }
  }, [pipelineRunning, scheduleDismiss]);

  return (
    <div className="min-h-screen flex bg-terminal-bg">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-56 bg-terminal-card border-r border-terminal-border
        transform transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        <div className="h-14 flex items-center justify-between px-4 border-b border-terminal-border">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-accent-blue flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-gray-100 tracking-wide">
              DLQI
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="p-3 space-y-0.5">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors
                  ${isActive ? "bg-accent-blue/15 text-accent-blue" : "text-gray-400 hover:text-gray-200 hover:bg-terminal-hover"}`}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-terminal-border">
          <div className="flex items-center gap-2 px-3 py-2">
            <div className="w-2 h-2 rounded-full bg-gain animate-pulse" />
            <span className="text-xs text-gray-400">系统运行正常</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center justify-between px-4 md:px-6 border-b border-terminal-border bg-terminal-card/80 backdrop-blur-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden text-gray-400 hover:text-white"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="hidden md:block">
            <input
              type="text"
              placeholder="搜索..."
              className="t-input !py-1.5 text-sm w-64"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRunPipeline}
              disabled={pipelineRunning}
              className="t-btn text-sm !py-1.5 flex items-center gap-1.5 disabled:opacity-60"
            >
              {pipelineRunning ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Activity className="w-3.5 h-3.5" />
              )}
              {pipelineRunning ? "运行中..." : "运行回测"}
            </button>
          </div>
        </header>

        {/* Pipeline notification bar */}
        {pipelineMsg && (
          <div
            className={`px-4 py-2 text-xs flex items-center gap-2 border-b border-terminal-border ${
              pipelineMsg.type === "success"
                ? "bg-gain/10 text-gain"
                : pipelineMsg.type === "error"
                  ? "bg-loss/10 text-loss"
                  : "bg-accent-blue/10 text-accent-blue"
            }`}
          >
            {pipelineMsg.type === "success" ? (
              <CheckCircle className="w-3.5 h-3.5" />
            ) : pipelineMsg.type === "error" ? (
              <XCircle className="w-3.5 h-3.5" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            )}
            {pipelineMsg.text}
            <button
              onClick={() => setPipelineMsg(null)}
              className="ml-auto text-gray-500 hover:text-gray-300"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        <main className="flex-1 p-4 md:p-6 overflow-auto scrollbar-thin">
          {children}
        </main>
      </div>
    </div>
  );
}
