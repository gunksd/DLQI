"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Database,
  Download,
  Upload,
  RefreshCw,
  Search,
  Plus,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
  XCircle,
  HardDrive,
  Cloud,
  FileText,
} from "lucide-react";
import {
  useDataSources,
  useStocks,
  useStockData,
  useDataQuality,
  useStorageStats,
  useSyncData,
} from "@/lib";

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
  type: string;
  status: string;
  lastSync: string | null;
  records: number;
  size: string;
  delay?: number;
}) {
  const statusConfig: Record<string, { color: string; label: string; icon: React.ElementType }> = {
    connected: { color: "clay-badge-success", label: "已连接", icon: CheckCircle },
    available: { color: "clay-badge-info", label: "可用", icon: Clock },
    error: { color: "clay-badge-danger", label: "错误", icon: XCircle },
    syncing: { color: "clay-badge-warning", label: "同步中", icon: RefreshCw },
  };

  const typeConfig: Record<string, { icon: React.ElementType; label: string }> = {
    aggregator: { icon: Cloud, label: "平台" },
    provider: { icon: Cloud, label: "数据源" },
    api: { icon: Cloud, label: "API" },
    file: { icon: FileText, label: "文件" },
    database: { icon: Database, label: "数据库" },
  };

  const config = statusConfig[status] || statusConfig.available;
  const typeInfo = typeConfig[type] || typeConfig.api;
  const StatusIcon = config.icon;
  const TypeIcon = typeInfo.icon;

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
            <p className="text-sm text-slate-400">{typeInfo.label}</p>
          </div>
        </div>
        <span className={`clay-badge ${config.color} flex items-center gap-1`}>
          <StatusIcon className={`w-3 h-3 ${status === "syncing" ? "animate-spin" : ""}`} />
          {config.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">记录数</div>
          <div className="font-medium text-slate-200">{records.toLocaleString()}</div>
        </div>
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">大小</div>
          <div className="font-medium text-slate-200">{size}</div>
        </div>
        <div className="p-2 rounded-clay-sm bg-dark-800/50 text-center">
          <div className="text-xs text-slate-500">更新</div>
          <div className="font-medium text-slate-200 text-xs">
            {lastSync ? new Date(lastSync).toLocaleTimeString() : "N/A"}
          </div>
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
      </div>
    </motion.div>
  );
}

// 股票列表 - 使用真实数据
function StockList() {
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useStocks({
    search: searchTerm || undefined,
    page,
    page_size: 10,
  });

  const syncMutation = useSyncData();

  const handleSync = async (symbol: string) => {
    const endDate = new Date().toISOString().split("T")[0];
    const startDate = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

    await syncMutation.mutateAsync({
      symbols: [symbol],
      start_date: startDate,
      end_date: endDate,
    });
  };

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
          <button
            onClick={() => refetch()}
            className="clay-button-secondary !px-3 !py-2"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
          <button className="clay-button !px-3 !py-2 text-sm flex items-center gap-1">
            <Plus className="w-4 h-4" />
            添加
          </button>
        </div>
      </div>

      {error ? (
        <div className="text-center py-8 text-red-400">
          加载失败: {error.message}
        </div>
      ) : isLoading ? (
        <div className="text-center py-8 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
          加载中...
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="clay-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>行业</th>
                  <th>记录数</th>
                  <th>最后更新</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((stock) => (
                  <tr key={stock.symbol}>
                    <td className="font-medium text-slate-200">{stock.symbol}</td>
                    <td className="text-slate-400">{stock.name}</td>
                    <td className="text-slate-500">{stock.sector}</td>
                    <td>{stock.records.toLocaleString()}</td>
                    <td className="text-slate-500">
                      {new Date(stock.last_update).toLocaleDateString()}
                    </td>
                    <td>
                      <span
                        className={`clay-badge ${
                          stock.status === "updated" ? "clay-badge-success" : "clay-badge-warning"
                        }`}
                      >
                        {stock.status === "updated" ? "已更新" : "待更新"}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleSync(stock.symbol)}
                          className="p-1.5 rounded hover:bg-dark-700"
                          disabled={syncMutation.isPending}
                        >
                          <RefreshCw
                            className={`w-4 h-4 text-slate-400 ${
                              syncMutation.isPending ? "animate-spin" : ""
                            }`}
                          />
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

          {/* 分页 */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-dark-700">
            <span className="text-sm text-slate-400">
              共 {data?.total || 0} 条记录
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="clay-button-secondary !px-3 !py-1 text-sm disabled:opacity-50"
              >
                上一页
              </button>
              <span className="px-3 py-1 text-slate-400">第 {page} 页</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data || data.items.length < 10}
                className="clay-button-secondary !px-3 !py-1 text-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// 数据质量面板 - 使用真实数据
function DataQualityPanel() {
  const { data, isLoading } = useDataQuality();

  const metrics = data
    ? [
        { name: "完整性", score: data.completeness, status: data.completeness >= 95 ? "good" : "warning" },
        { name: "准确性", score: data.accuracy, status: data.accuracy >= 95 ? "good" : "warning" },
        { name: "一致性", score: data.consistency, status: data.consistency >= 95 ? "good" : "warning" },
        { name: "时效性", score: data.timeliness, status: data.timeliness >= 95 ? "good" : "warning" },
      ]
    : [];

  return (
    <div className="clay-card">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">数据质量</h3>
      {isLoading ? (
        <div className="text-center py-4 text-slate-400">加载中...</div>
      ) : (
        <>
          <div className="space-y-4">
            {metrics.map((metric) => (
              <div key={metric.name}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-slate-300">{metric.name}</span>
                  <span
                    className={`font-medium ${
                      metric.status === "good" ? "text-neon-green" : "text-yellow-400"
                    }`}
                  >
                    {metric.score.toFixed(1)}%
                  </span>
                </div>
                <div className="clay-progress">
                  <div
                    className={`clay-progress-bar ${metric.status === "warning" ? "!bg-yellow-500" : ""}`}
                    style={{ width: `${metric.score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-dark-700">
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <CheckCircle className="w-4 h-4 text-neon-green" />
              <span>整体评分: {data?.overall.toFixed(1)}%</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// 存储统计 - 使用真实数据
function StorageStats() {
  const { data, isLoading } = useStorageStats();

  if (isLoading || !data) {
    return (
      <div className="clay-card">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">存储使用</h3>
        <div className="text-center py-4 text-slate-400">加载中...</div>
      </div>
    );
  }

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">存储使用</h3>
        <span className="text-sm text-slate-400">
          {data.total_size_gb.toFixed(1)} / {data.max_size_gb} GB
        </span>
      </div>

      {/* 存储条 */}
      <div className="h-4 rounded-full bg-dark-700 overflow-hidden flex mb-4">
        {data.items.map((item) => (
          <div
            key={item.name}
            style={{
              width: `${(item.size_gb / data.max_size_gb) * 100}%`,
              backgroundColor: item.color,
            }}
            className="h-full"
          ></div>
        ))}
      </div>

      {/* 图例 */}
      <div className="grid grid-cols-2 gap-2">
        {data.items.map((item) => (
          <div key={item.name} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }}
            ></div>
            <span className="text-sm text-slate-400">{item.name}</span>
            <span className="text-sm text-slate-500 ml-auto">{item.size_gb} GB</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// 数据预览 - 使用真实数据
function DataPreview() {
  const [symbol, setSymbol] = useState("AAPL");
  const { data, isLoading, error } = useStockData(symbol, {
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
  });

  return (
    <div className="clay-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100">数据预览 - {symbol}</h3>
        <div className="flex items-center gap-2">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="clay-select !py-2 !px-3 text-sm w-32"
          >
            <option value="AAPL">AAPL</option>
            <option value="GOOGL">GOOGL</option>
            <option value="MSFT">MSFT</option>
            <option value="NVDA">NVDA</option>
            <option value="TSLA">TSLA</option>
          </select>
          <button className="clay-button-secondary !px-3 !py-2">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error ? (
        <div className="text-center py-8 text-red-400">
          加载失败: {error.message}
        </div>
      ) : isLoading ? (
        <div className="text-center py-8 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
          加载中...
        </div>
      ) : (
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
                <th>涨跌幅</th>
              </tr>
            </thead>
            <tbody>
              {data?.data.slice(-10).reverse().map((row) => (
                <tr key={row.date}>
                  <td className="font-medium text-slate-200">
                    {new Date(row.date).toLocaleDateString()}
                  </td>
                  <td>${row.open.toFixed(2)}</td>
                  <td className="text-neon-green">${row.high.toFixed(2)}</td>
                  <td className="text-red-400">${row.low.toFixed(2)}</td>
                  <td>${row.close.toFixed(2)}</td>
                  <td className="text-slate-400">
                    {(row.volume / 1000000).toFixed(1)}M
                  </td>
                  <td className={row.pct_change && row.pct_change >= 0 ? "text-neon-green" : "text-red-400"}>
                    {row.pct_change ? `${row.pct_change >= 0 ? "+" : ""}${row.pct_change.toFixed(2)}%` : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-2 text-sm text-slate-500 text-right">
            共 {data?.records} 条记录 | 数据源: {data?.provider}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DataPage() {
  const { data: sources, isLoading: sourcesLoading } = useDataSources();

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
        {sourcesLoading ? (
          <div className="col-span-4 text-center py-8 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            加载数据源...
          </div>
        ) : (
          sources?.map((source, index) => (
            <DataSourceCard
              key={source.name}
              name={source.name}
              type={source.type}
              status={source.status}
              lastSync={source.last_sync}
              records={source.records}
              size={source.size}
              delay={index * 0.1}
            />
          ))
        )}
      </div>

      {/* 股票列表 */}
      <StockList />

      {/* 数据质量和存储 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <DataQualityPanel />
        <StorageStats />
      </div>

      {/* 数据预览 */}
      <DataPreview />
    </div>
  );
}
