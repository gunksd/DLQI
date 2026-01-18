"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Database,
  Download,
  Upload,
  RefreshCw,
  Search,
  Filter,
  Plus,
  Trash2,
  Edit,
  Eye,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  HardDrive,
  Cloud,
  FileText,
  BarChart3,
  TrendingUp
} from "lucide-react";

// 数据源卡片
function DataSourceCard({
  name,
  type,
  status,
  lastSync,
  records,
  size,
  delay = 0,
}: {
  name: string;
  type: "api" | "file" | "database";
  status: "connected" | "error" | "syncing";
  lastSync: string;
  records: string;
  size: string;
  delay?: number;
}) {
  const statusConfig = {
    connected: { color: "clay-badge-success", label: "已连接", icon: CheckCircle },
    error: { color: "clay-badge-danger", label: "错误", icon: XCircle },
    syncing: { color: "clay-badge-warning", label: "同步中", icon: RefreshCw },
  };

  const typeConfig = {
    api: { icon: Cloud, label: "API" },
    file: { icon: FileText, label: "文件" },
    database: { icon: Database, label: "数据库" },
  };

  const StatusIcon = statusConfig[status].icon;
  const TypeIcon = typeConfig[type].icon;

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
            <TypeIcon className="w-6 h-6 text-neon-blue" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">{name}</h3>
            <p className="text-sm text-slate-400">{typeConfig[type].label}</p>
          </div>
        </div>
        <span className={`clay-badge ${statusConfig[status].color} flex items-center gap-1`}>
          <StatusIcon className={`w-3 h-3 ${status === "syncing" ? "animate-spin" : ""}`} />
          {statusConfig[status].label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">记录数</div>
          <div className="font-medium text-slate-200">{records}</div>
        </div>
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">大小</div>
          <div className="font-medium text-slate-200">{size}</div>
        </div>
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">更新</div>
          <div className="font-medium text-slate-200">{lastSync}</div>
        </div>
      </div>

      <div className="flex gap-2">
        <button className="flex-1 clay-button-secondary !py-2 text-sm flex items-center justify-center gap-1">
          <RefreshCw className="w-4 h-4" />
          同步
        </button>
        <button className="clay-button-secondary !px-3 !py-2">
          <Eye className="w-4 h-4" />
        </button>
        <button className="clay-button-secondary !px-3 !py-2">
          <Edit className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  );
}

// 股票列表
function StockList() {
  const stocks = [
    { symbol: "AAPL", name: "苹果公司", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
    { symbol: "GOOGL", name: "谷歌", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
    { symbol: "MSFT", name: "微软", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
    { symbol: "NVDA", name: "英伟达", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
    { symbol: "TSLA", name: "特斯拉", records: "2,520", lastUpdate: "昨天 15:00", status: "outdated" },
    { symbol: "AMZN", name: "亚马逊", records: "2,520", lastUpdate: "昨天 15:00", status: "outdated" },
    { symbol: "META", name: "Meta", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
    { symbol: "NFLX", name: "奈飞", records: "2,520", lastUpdate: "今天 09:30", status: "updated" },
  ];

  const [searchTerm, setSearchTerm] = useState("");

  const filteredStocks = stocks.filter(
    (stock) =>
      stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stock.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">股票数据</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="搜索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="clay-input !pl-9 !py-2 text-sm w-48"
            />
          </div>
          <button className="clay-button !px-3 !py-2 text-sm flex items-center gap-1">
            <Plus className="w-4 h-4" />
            添加
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>记录数</th>
              <th>最后更新</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map((stock) => (
              <tr key={stock.symbol}>
                <td className="font-medium text-slate-200">{stock.symbol}</td>
                <td className="text-slate-400">{stock.name}</td>
                <td>{stock.records}</td>
                <td className="text-slate-500">{stock.lastUpdate}</td>
                <td>
                  <span className={`clay-badge ${
                    stock.status === "updated" ? "clay-badge-success" : "clay-badge-warning"
                  }`}>
                    {stock.status === "updated" ? "已更新" : "待更新"}
                  </span>
                </td>
                <td>
                  <div className="flex items-center gap-1">
                    <button className="p-1.5 rounded hover:bg-dark-700">
                      <RefreshCw className="w-4 h-4 text-slate-400" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-dark-700">
                      <Eye className="w-4 h-4 text-slate-400" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-dark-700">
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 数据质量面板
function DataQualityPanel() {
  const qualityMetrics = [
    { name: "完整性", score: 98.5, status: "good" },
    { name: "准确性", score: 99.2, status: "good" },
    { name: "一致性", score: 97.8, status: "good" },
    { name: "时效性", score: 92.3, status: "warning" },
  ];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">数据质量</h3>
      <div className="space-y-4">
        {qualityMetrics.map((metric) => (
          <div key={metric.name}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300">{metric.name}</span>
              <span className={`font-medium ${
                metric.status === "good" ? "text-neon-green" : "text-yellow-400"
              }`}>
                {metric.score}%
              </span>
            </div>
            <div className="clay-progress">
              <div
                className={`clay-progress-bar ${
                  metric.status === "warning" ? "!bg-yellow-500" : ""
                }`}
                style={{ width: `${metric.score}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <CheckCircle className="w-4 h-4 text-neon-green" />
          <span>数据质量整体良好</span>
        </div>
      </div>
    </div>
  );
}

// 存储统计
function StorageStats() {
  const storageItems = [
    { name: "价格数据", size: 2.5, color: "bg-neon-blue" },
    { name: "特征数据", size: 1.8, color: "bg-neon-purple" },
    { name: "模型文件", size: 0.8, color: "bg-neon-green" },
    { name: "回测结果", size: 0.5, color: "bg-yellow-400" },
    { name: "日志文件", size: 0.3, color: "bg-orange-400" },
  ];

  const totalSize = storageItems.reduce((a, b) => a + b.size, 0);
  const maxSize = 10; // GB

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">存储使用</h3>
        <span className="text-sm text-slate-400">{totalSize.toFixed(1)} / {maxSize} GB</span>
      </div>

      {/* 存储条 */}
      <div className="h-4 rounded-full bg-dark-700 overflow-hidden flex mb-4">
        {storageItems.map((item, index) => (
          <div
            key={item.name}
            className={`h-full ${item.color}`}
            style={{ width: `${(item.size / maxSize) * 100}%` }}
          ></div>
        ))}
      </div>

      {/* 图例 */}
      <div className="grid grid-cols-2 gap-2">
        {storageItems.map((item) => (
          <div key={item.name} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${item.color}`}></div>
            <span className="text-sm text-slate-400">{item.name}</span>
            <span className="text-sm text-slate-500 ml-auto">{item.size} GB</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// 同步任务
function SyncTasks() {
  const tasks = [
    { name: "获取AAPL日线数据", status: "completed", time: "2分钟前" },
    { name: "计算技术指标", status: "running", time: "进行中" },
    { name: "更新特征矩阵", status: "pending", time: "待执行" },
    { name: "同步Yahoo Finance", status: "completed", time: "10分钟前" },
  ];

  const statusConfig = {
    completed: { icon: CheckCircle, color: "text-neon-green" },
    running: { icon: RefreshCw, color: "text-yellow-400" },
    pending: { icon: Clock, color: "text-slate-400" },
  };

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">同步任务</h3>
        <button className="clay-button-secondary !px-3 !py-2 text-sm">
          查看全部
        </button>
      </div>
      <div className="space-y-3">
        {tasks.map((task, index) => {
          const config = statusConfig[task.status as keyof typeof statusConfig];
          const Icon = config.icon;
          return (
            <div key={index} className="flex items-center gap-3 p-3 rounded-clay-sm bg-dark-800/50">
              <Icon className={`w-5 h-5 ${config.color} ${
                task.status === "running" ? "animate-spin" : ""
              }`} />
              <div className="flex-1">
                <div className="text-sm text-slate-200">{task.name}</div>
              </div>
              <span className="text-xs text-slate-500">{task.time}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 数据预览
function DataPreview() {
  const previewData = [
    { date: "2025-01-17", open: 185.32, high: 186.45, low: 184.12, close: 185.89, volume: "52.3M" },
    { date: "2025-01-16", open: 184.56, high: 185.78, low: 183.90, close: 185.32, volume: "48.1M" },
    { date: "2025-01-15", open: 183.25, high: 184.80, low: 182.50, close: 184.56, volume: "55.8M" },
    { date: "2025-01-14", open: 182.10, high: 183.65, low: 181.20, close: 183.25, volume: "42.5M" },
    { date: "2025-01-13", open: 181.45, high: 182.90, low: 180.80, close: 182.10, volume: "38.2M" },
  ];

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">数据预览 - AAPL</h3>
        <div className="flex items-center gap-2">
          <select className="clay-select !py-2 !px-3 text-sm w-32">
            <option>AAPL</option>
            <option>GOOGL</option>
            <option>MSFT</option>
          </select>
          <button className="clay-button-secondary !px-3 !py-2">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="clay-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>开盘</th>
              <th>最高</th>
              <th>最低</th>
              <th>收盘</th>
              <th>成交量</th>
            </tr>
          </thead>
          <tbody>
            {previewData.map((row) => (
              <tr key={row.date}>
                <td className="font-medium text-slate-200">{row.date}</td>
                <td>${row.open.toFixed(2)}</td>
                <td className="text-neon-green">${row.high.toFixed(2)}</td>
                <td className="text-red-400">${row.low.toFixed(2)}</td>
                <td>${row.close.toFixed(2)}</td>
                <td className="text-slate-400">{row.volume}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DataPage() {
  const dataSources = [
    {
      name: "Yahoo Finance",
      type: "api" as const,
      status: "connected" as const,
      lastSync: "5分钟前",
      records: "125K",
      size: "850 MB",
    },
    {
      name: "Tushare Pro",
      type: "api" as const,
      status: "connected" as const,
      lastSync: "10分钟前",
      records: "89K",
      size: "620 MB",
    },
    {
      name: "本地CSV文件",
      type: "file" as const,
      status: "connected" as const,
      lastSync: "1小时前",
      records: "45K",
      size: "320 MB",
    },
    {
      name: "PostgreSQL",
      type: "database" as const,
      status: "syncing" as const,
      lastSync: "同步中...",
      records: "258K",
      size: "1.8 GB",
    },
  ];

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">数据管理</h1>
          <p className="text-slate-400 text-sm mt-1">
            管理数据源、同步任务和数据质量
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="clay-button-secondary flex items-center gap-2">
            <Upload className="w-4 h-4" />
            导入数据
          </button>
          <button className="clay-button flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            全部同步
          </button>
        </div>
      </div>

      {/* 数据源卡片 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {dataSources.map((source, index) => (
          <DataSourceCard key={source.name} {...source} delay={index * 0.1} />
        ))}
      </div>

      {/* 股票列表 */}
      <StockList />

      {/* 数据质量、存储和任务 */}
      <div className="grid lg:grid-cols-3 gap-6">
        <DataQualityPanel />
        <StorageStats />
        <SyncTasks />
      </div>

      {/* 数据预览 */}
      <DataPreview />
    </div>
  );
}
