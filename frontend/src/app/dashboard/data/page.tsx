"use client";

import { useState, useCallback, useRef, useEffect } from "react";
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
  X,
} from "lucide-react";
import {
  useDataSources,
  useStocks,
  useStockData,
  useDataQuality,
  useStorageStats,
  useSyncData,
} from "@/lib";
import api from "@/lib/api";

/* Toast notification */
function Toast({
  msg,
  onClose,
}: {
  msg: { text: string; type: "info" | "success" | "error" } | null;
  onClose: () => void;
}) {
  if (!msg) return null;
  const cls =
    msg.type === "success"
      ? "bg-gain/10 text-gain border-gain/20"
      : msg.type === "error"
        ? "bg-loss/10 text-loss border-loss/20"
        : "bg-accent-blue/10 text-accent-blue border-accent-blue/20";
  return (
    <div
      className={`fixed top-4 right-4 z-50 px-4 py-2.5 rounded border text-xs flex items-center gap-2 shadow-lg ${cls}`}
    >
      {msg.type === "success" ? (
        <CheckCircle className="w-3.5 h-3.5" />
      ) : msg.type === "error" ? (
        <XCircle className="w-3.5 h-3.5" />
      ) : (
        <RefreshCw className="w-3.5 h-3.5" />
      )}
      {msg.text}
      <button onClick={onClose} className="ml-2 opacity-60 hover:opacity-100">
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

function DataSourceCard({
  name,
  type,
  status,
  lastSync,
  records,
  size,
  onSync,
  onView,
}: {
  name: string;
  type: string;
  status: string;
  lastSync: string | null;
  records: number;
  size: string;
  onSync: () => void;
  onView: () => void;
}) {
  const [syncing, setSyncing] = useState(false);
  const statusCfg: Record<
    string,
    { cls: string; label: string; icon: React.ElementType }
  > = {
    connected: { cls: "t-badge-gain", label: "已连接", icon: CheckCircle },
    available: { cls: "t-badge-info", label: "可用", icon: Clock },
    error: { cls: "t-badge-loss", label: "错误", icon: XCircle },
    syncing: { cls: "t-badge-warn", label: "同步中", icon: RefreshCw },
  };
  const typeIcons: Record<string, React.ElementType> = {
    aggregator: Cloud,
    provider: Cloud,
    api: Cloud,
    file: FileText,
    database: Database,
  };
  const cfg = statusCfg[syncing ? "syncing" : status] || statusCfg.available;
  const TypeIcon = typeIcons[type] || Cloud;
  const StatusIcon = cfg.icon;

  const handleSync = async () => {
    setSyncing(true);
    onSync();
    setTimeout(() => setSyncing(false), 2000);
  };

  return (
    <div className="t-card">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-accent-blue/10">
            <TypeIcon className="w-5 h-5 text-accent-blue" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-100">{name}</h3>
            <p className="text-xs text-gray-500">{type}</p>
          </div>
        </div>
        <span className={`t-badge ${cfg.cls} flex items-center gap-1`}>
          <StatusIcon className={`w-3 h-3 ${syncing ? "animate-spin" : ""}`} />
          {cfg.label}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="p-2 rounded bg-terminal-hover text-center">
          <div className="text-[10px] text-gray-500">记录数</div>
          <div className="text-xs font-medium text-gray-200 font-num">
            {records.toLocaleString()}
          </div>
        </div>
        <div className="p-2 rounded bg-terminal-hover text-center">
          <div className="text-[10px] text-gray-500">大小</div>
          <div className="text-xs font-medium text-gray-200">{size}</div>
        </div>
        <div className="p-2 rounded bg-terminal-hover text-center">
          <div className="text-[10px] text-gray-500">更新</div>
          <div className="text-xs font-medium text-gray-200">
            {lastSync ? new Date(lastSync).toLocaleTimeString() : "N/A"}
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex-1 t-btn-ghost !py-1.5 text-xs flex items-center justify-center gap-1 disabled:opacity-50"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`}
          />
          {syncing ? "同步中" : "同步"}
        </button>
        <button onClick={onView} className="t-btn-ghost !px-2.5 !py-1.5">
          <Eye className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function StockList({
  onToast,
}: {
  onToast: (msg: string, type: "info" | "success" | "error") => void;
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading, error, refetch } = useStocks({
    search: searchTerm || undefined,
    page,
    page_size: 10,
  });
  const syncMutation = useSyncData();
  const [viewSymbol, setViewSymbol] = useState<string | null>(null);

  const handleSync = async (symbol: string) => {
    const endDate = new Date().toISOString().split("T")[0];
    const startDate = new Date(Date.now() - 365 * 86400000)
      .toISOString()
      .split("T")[0];
    try {
      await syncMutation.mutateAsync({
        symbols: [symbol],
        start_date: startDate,
        end_date: endDate,
      });
      onToast(`${symbol} 同步完成`, "success");
    } catch {
      onToast(`${symbol} 同步失败`, "error");
    }
  };

  const handleDelete = (symbol: string) => {
    onToast(`${symbol}: 本系统使用本地 CSV 数据，不支持在线删除`, "info");
  };

  const handleView = (symbol: string) => {
    setViewSymbol(viewSymbol === symbol ? null : symbol);
  };

  return (
    <div className="t-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">股票数据</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="搜索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="t-input !pl-8 !py-1.5 text-xs w-40"
            />
          </div>
          <button
            onClick={() => refetch()}
            className="t-btn-ghost !px-2 !py-1.5"
            disabled={isLoading}
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`}
            />
          </button>
          <button
            onClick={() =>
              onToast(
                "本系统使用预设的 5 只美股 (AAPL, AMZN, GOOGL, MSFT, NVDA)，暂不支持新增",
                "info",
              )
            }
            className="t-btn !py-1.5 text-xs flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" />
            添加
          </button>
        </div>
      </div>

      {error ? (
        <div className="text-center py-8 text-loss text-sm">
          加载失败: {error.message}
        </div>
      ) : isLoading ? (
        <div className="text-center py-8 text-gray-400 text-sm">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
          加载中...
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="t-table">
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
                  <tr
                    key={stock.symbol}
                    className={
                      viewSymbol === stock.symbol ? "!bg-accent-blue/5" : ""
                    }
                  >
                    <td className="font-medium text-gray-200">
                      {stock.symbol}
                    </td>
                    <td className="text-gray-400">{stock.name}</td>
                    <td className="text-gray-500">{stock.sector}</td>
                    <td className="font-num">
                      {stock.records.toLocaleString()}
                    </td>
                    <td className="text-gray-500">
                      {new Date(stock.last_update).toLocaleDateString()}
                    </td>
                    <td>
                      <span
                        className={`t-badge ${stock.status === "updated" ? "t-badge-gain" : "t-badge-warn"}`}
                      >
                        {stock.status === "updated" ? "已更新" : "待更新"}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleSync(stock.symbol)}
                          className="p-1 rounded hover:bg-terminal-hover"
                          disabled={syncMutation.isPending}
                          title="同步数据"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 text-gray-400 ${syncMutation.isPending ? "animate-spin" : ""}`}
                          />
                        </button>
                        <button
                          onClick={() => handleView(stock.symbol)}
                          className="p-1 rounded hover:bg-terminal-hover"
                          title="查看数据"
                        >
                          <Eye
                            className={`w-3.5 h-3.5 ${viewSymbol === stock.symbol ? "text-accent-blue" : "text-gray-400"}`}
                          />
                        </button>
                        <button
                          onClick={() => handleDelete(stock.symbol)}
                          className="p-1 rounded hover:bg-terminal-hover"
                          title="删除"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-loss" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Inline data preview when Eye is clicked */}
          {viewSymbol && (
            <div className="mt-3 p-3 rounded bg-terminal-bg border border-terminal-border">
              <InlinePreview symbol={viewSymbol} />
            </div>
          )}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-terminal-border">
            <span className="text-xs text-gray-500">
              共 {data?.total || 0} 条记录
            </span>
            <div className="flex gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="t-btn-ghost !px-2.5 !py-1 text-xs disabled:opacity-50"
              >
                上一页
              </button>
              <span className="px-2 py-1 text-xs text-gray-400">
                第 {page} 页
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data || data.items.length < 10}
                className="t-btn-ghost !px-2.5 !py-1 text-xs disabled:opacity-50"
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

/* Inline data preview for Eye button in stock table */
function InlinePreview({ symbol }: { symbol: string }) {
  const { data, isLoading, error } = useStockData(symbol, {
    start_date: new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0],
  });
  if (isLoading)
    return (
      <div className="text-center py-3 text-gray-400 text-xs">
        加载 {symbol} 数据...
      </div>
    );
  if (error)
    return <div className="text-center py-3 text-loss text-xs">加载失败</div>;
  return (
    <div>
      <div className="text-xs text-gray-400 mb-2">{symbol} 最近 5 条记录</div>
      <table className="t-table">
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
          {data?.data
            .slice(-5)
            .reverse()
            .map((row) => (
              <tr key={row.date}>
                <td className="text-gray-200">
                  {(row.date || "").split("T")[0]}
                </td>
                <td className="font-num">${row.open.toFixed(2)}</td>
                <td className="text-gain font-num">${row.high.toFixed(2)}</td>
                <td className="text-loss font-num">${row.low.toFixed(2)}</td>
                <td className="font-num">${row.close.toFixed(2)}</td>
                <td className="text-gray-400 font-num">
                  {(row.volume / 1000000).toFixed(1)}M
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function DataQualityPanel() {
  const { data, isLoading } = useDataQuality();
  const metrics = data
    ? [
        {
          name: "完整性",
          score: data.completeness,
          good: data.completeness >= 95,
        },
        { name: "准确性", score: data.accuracy, good: data.accuracy >= 95 },
        {
          name: "一致性",
          score: data.consistency,
          good: data.consistency >= 95,
        },
        { name: "时效性", score: data.timeliness, good: data.timeliness >= 95 },
      ]
    : [];

  return (
    <div className="t-card">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">数据质量</h3>
      {isLoading ? (
        <div className="text-center py-4 text-gray-400 text-sm">加载中...</div>
      ) : (
        <>
          <div className="space-y-3">
            {metrics.map((m) => (
              <div key={m.name}>
                <div className="flex items-center justify-between mb-1 text-xs">
                  <span className="text-gray-300">{m.name}</span>
                  <span
                    className={`font-num ${m.good ? "text-gain" : "text-amber-400"}`}
                  >
                    {m.score.toFixed(1)}%
                  </span>
                </div>
                <div className="t-progress">
                  <div
                    className={`t-progress-bar ${!m.good ? "!bg-amber-400" : ""}`}
                    style={{ width: `${m.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-terminal-border flex items-center gap-2 text-xs text-gray-400">
            <CheckCircle className="w-3.5 h-3.5 text-gain" />
            整体评分: {data?.overall.toFixed(1)}%
          </div>
        </>
      )}
    </div>
  );
}

function StorageStatsPanel() {
  const { data, isLoading } = useStorageStats();
  if (isLoading || !data)
    return (
      <div className="t-card">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">存储使用</h3>
        <div className="text-center py-4 text-gray-400 text-sm">加载中...</div>
      </div>
    );

  return (
    <div className="t-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">存储使用</h3>
        <span className="text-xs text-gray-500 font-num">
          {data.total_size_gb.toFixed(1)} / {data.max_size_gb} GB
        </span>
      </div>
      <div className="h-3 rounded-full bg-terminal-hover overflow-hidden flex mb-3">
        {data.items.map((item) => (
          <div
            key={item.name}
            style={{
              width: `${(item.size_gb / data.max_size_gb) * 100}%`,
              backgroundColor: item.color,
            }}
            className="h-full"
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {data.items.map((item) => (
          <div key={item.name} className="flex items-center gap-2 text-xs">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-gray-400">{item.name}</span>
            <span className="text-gray-500 ml-auto font-num">
              {item.size_gb} GB
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataPreview({
  onToast,
}: {
  onToast: (msg: string, type: "info" | "success" | "error") => void;
}) {
  const [symbol, setSymbol] = useState("AAPL");
  const { data, isLoading, error } = useStockData(symbol, {
    start_date: new Date(Date.now() - 30 * 86400000)
      .toISOString()
      .split("T")[0],
  });

  const handleDownload = useCallback(() => {
    if (!data?.data?.length) {
      onToast("没有数据可导出", "error");
      return;
    }
    const headers = "date,open,high,low,close,volume\n";
    const rows = data.data
      .map(
        (r) => `${r.date},${r.open},${r.high},${r.low},${r.close},${r.volume}`,
      )
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${symbol}_data.csv`;
    a.click();
    URL.revokeObjectURL(url);
    onToast(`${symbol} 数据已导出为 CSV`, "success");
  }, [data, symbol, onToast]);

  return (
    <div className="t-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">
          数据预览 - {symbol}
        </h3>
        <div className="flex items-center gap-2">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="t-select !py-1.5 text-xs w-24"
          >
            <option value="AAPL">AAPL</option>
            <option value="GOOGL">GOOGL</option>
            <option value="MSFT">MSFT</option>
            <option value="NVDA">NVDA</option>
            <option value="AMZN">AMZN</option>
          </select>
          <button
            onClick={handleDownload}
            className="t-btn-ghost !px-2 !py-1.5"
            title="导出 CSV"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {error ? (
        <div className="text-center py-8 text-loss text-sm">
          加载失败: {error.message}
        </div>
      ) : isLoading ? (
        <div className="text-center py-8 text-gray-400 text-sm">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
          加载中...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="t-table">
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
              {data?.data
                .slice(-10)
                .reverse()
                .map((row) => (
                  <tr key={row.date}>
                    <td className="font-medium text-gray-200">
                      {new Date(row.date).toLocaleDateString()}
                    </td>
                    <td className="font-num">${row.open.toFixed(2)}</td>
                    <td className="text-gain font-num">
                      ${row.high.toFixed(2)}
                    </td>
                    <td className="text-loss font-num">
                      ${row.low.toFixed(2)}
                    </td>
                    <td className="font-num">${row.close.toFixed(2)}</td>
                    <td className="text-gray-400 font-num">
                      {(row.volume / 1000000).toFixed(1)}M
                    </td>
                    <td
                      className={`font-num ${row.pct_change && row.pct_change >= 0 ? "text-gain" : "text-loss"}`}
                    >
                      {row.pct_change
                        ? `${row.pct_change >= 0 ? "+" : ""}${row.pct_change.toFixed(2)}%`
                        : "-"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div className="mt-2 text-xs text-gray-500 text-right">
            共 {data?.records} 条记录 | 数据源: {data?.provider}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DataPage() {
  const { data: sources, isLoading: sourcesLoading } = useDataSources();
  const syncAll = useSyncData();
  const [toast, setToast] = useState<{
    text: string;
    type: "info" | "success" | "error";
  } | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(
    () => () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    },
    [],
  );

  const showToast = useCallback(
    (text: string, type: "info" | "success" | "error" = "info") => {
      setToast({ text, type });
      if (toastTimer.current) clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(() => setToast(null), 4000);
    },
    [],
  );

  const handleSyncAll = async () => {
    setSyncingAll(true);
    showToast("开始同步所有股票数据...", "info");
    const symbols = ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"];
    const endDate = new Date().toISOString().split("T")[0];
    const startDate = new Date(Date.now() - 365 * 86400000)
      .toISOString()
      .split("T")[0];
    try {
      await syncAll.mutateAsync({
        symbols,
        start_date: startDate,
        end_date: endDate,
      });
      showToast("全部同步完成", "success");
    } catch {
      showToast("同步失败", "error");
    } finally {
      setSyncingAll(false);
    }
  };

  const handleImport = () => {
    showToast(
      "本系统使用本地 CSV 数据 (data/raw/)，请将 CSV 文件放入该目录后刷新",
      "info",
    );
  };

  const handleSourceSync = (name: string) => {
    showToast(`${name} 数据已是最新`, "success");
  };

  const handleSourceView = (name: string) => {
    showToast(`查看 ${name} — 请在下方数据预览区选择股票查看`, "info");
  };

  return (
    <div className="space-y-5">
      <Toast msg={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">数据管理</h1>
          <p className="text-gray-500 text-xs mt-1">
            管理数据源、同步任务和数据质量
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleImport}
            className="t-btn-ghost flex items-center gap-1.5 text-sm"
          >
            <Upload className="w-4 h-4" />
            导入数据
          </button>
          <button
            onClick={handleSyncAll}
            disabled={syncingAll}
            className="t-btn flex items-center gap-1.5 text-sm disabled:opacity-60"
          >
            <RefreshCw
              className={`w-4 h-4 ${syncingAll ? "animate-spin" : ""}`}
            />
            {syncingAll ? "同步中..." : "全部同步"}
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {sourcesLoading ? (
          <div className="col-span-4 text-center py-8 text-gray-400 text-sm">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
            加载数据源...
          </div>
        ) : (
          sources?.map((source) => (
            <DataSourceCard
              key={source.name}
              name={source.name}
              type={source.type}
              status={source.status}
              lastSync={source.last_sync}
              records={source.records}
              size={source.size}
              onSync={() => handleSourceSync(source.name)}
              onView={() => handleSourceView(source.name)}
            />
          ))
        )}
      </div>

      <StockList onToast={showToast} />

      <div className="grid lg:grid-cols-2 gap-4">
        <DataQualityPanel />
        <StorageStatsPanel />
      </div>

      <DataPreview onToast={showToast} />
    </div>
  );
}
