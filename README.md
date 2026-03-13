# DLQI — 基于深度学习的量化投资系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 一个完整的量化交易研究平台，集成 4 种机器学习模型（LSTM、Transformer、LightGBM、XGBoost），覆盖 5 只美股（AAPL、AMZN、GOOGL、MSFT、NVDA），提供策略回测、风险分析和可视化仪表盘。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│          前端 (Next.js 14 + TailwindCSS + ECharts)              │
│          Bloomberg Terminal 深色主题 · 9 种专业图表              │
├─────────────────────────────────────────────────────────────────┤
│            REST API (FastAPI + Uvicorn)                          │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│ 数据管道  │ 特征工程  │ 模型训练  │ 策略回测  │ 风控分析          │
├──────────┴──────────┴──────────┴──────────┴─────────────────────┤
│     CSV 数据存储 · PyTorch · LightGBM · XGBoost · Backtrader    │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+（已测试 v23.3.0）

### 安装

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 启动服务

**方式一：直接启动**

```bash
# 终端 1 — 后端（端口 8000）
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 前端（端口 3000）
cd frontend
npx next dev
```

**方式二：tmux 一键启动**

```bash
# 启动后端
tmux new-session -d -s backend \
  "cd $(pwd)/backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

# 启动前端
tmux new-session -d -s dev \
  "cd $(pwd)/frontend && npx next dev"
```

### 访问地址

| 服务 | URL |
|------|-----|
| 前端仪表盘 | http://localhost:3000 |
| API 文档（Swagger） | http://localhost:8000/api/docs |
| API 文档（ReDoc） | http://localhost:8000/api/redoc |

## 项目结构

```
DLQI/
├── backend/                # FastAPI 后端
│   ├── main.py             # 入口
│   ├── app/
│   │   ├── api/            # API 路由（data, models, backtest, risk, strategies）
│   │   ├── services/       # 业务逻辑（数据、特征、模型、回测、风控）
│   │   └── core/           # 配置
│   └── requirements.txt
├── frontend/               # Next.js 14 前端
│   └── src/
│       ├── app/
│       │   └── dashboard/  # 7 个仪表盘页面
│       ├── components/
│       │   └── charts/     # 9 个 ECharts 图表组件（懒加载）
│       └── lib/            # API 客户端 + React Query hooks
├── data/
│   ├── raw/                # 原始股票 CSV 数据
│   ├── features/           # 特征工程输出
│   ├── models/             # 训练好的模型文件（20 个）
│   ├── processed/          # 预处理数据
│   └── backtest_results/   # 回测权益曲线
└── results/                # 回测结果 CSV + 模型分析
```

## 仪表盘页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 控制台概览 | `/dashboard` | 系统整体状态、模型性能概览、Top 5 排行 |
| 策略分析 | `/dashboard/strategies` | 主策略推荐、K线图+交易信号、收益曲线 |
| 模型对比 | `/dashboard/models` | 20 个模型详情、性能对比表、特征重要性 |
| 回测结果 | `/dashboard/backtest` | Sharpe 热力图、模型类型对比、完整回测数据 |
| 风险监控 | `/dashboard/risk` | VaR 走势、回撤分析、相关性矩阵、压力测试 |
| 数据管理 | `/dashboard/data` | 数据源状态、股票数据浏览、质量评分 |
| 参数调优 | `/dashboard/tuning` | 优化趋势图、模型类型横向对比 |

## 模型性能（真实回测数据）

### 模型类型平均表现

| 模型类型 | 平均夏普比率 | 平均总收益 | 平均方向准确率 |
|---------|------------|-----------|--------------|
| XGBoost | 1.27 | 31.1% | 50.5% |
| LightGBM | 0.90 | 33.9% | 54.6% |
| BiLSTM+Attn | 0.84 | 27.8% | 47.6% |
| Transformer | 0.44 | 7.9% | 47.1% |

### Top 5 最佳策略（按 Sharpe 排序）

| 排名 | 模型 | 股票 | 夏普比率 | 总收益 | 最大回撤 |
|-----|------|------|---------|-------|---------|
| 1 | LightGBM | NVDA | 2.57 | 123.8% | -27.0% |
| 2 | LSTM | NVDA | 2.57 | 123.8% | -27.0% |
| 3 | XGBoost | NVDA | 2.56 | 96.4% | -15.7% |
| 4 | LightGBM | AAPL | 1.45 | 30.1% | -15.2% |
| 5 | XGBoost | AAPL | 1.31 | 17.4% | -13.9% |

**主策略**: LightGBM — NVDA（Sharpe 2.57）。LightGBM 梯度提升树擅长捕捉非线性特征交互，使用 60×12=720 维特征矩阵，内置正则化在小样本上不易过拟合。

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI | Web 框架 + REST API |
| PyTorch | LSTM / Transformer 深度学习模型 |
| LightGBM / XGBoost | 梯度提升模型 |
| Backtrader | 回测引擎 |
| Pandas / NumPy | 数据处理 |
| Scikit-learn | 特征工程 + 模型评估 |
| Optuna | 超参数优化 |

### 前端

| 技术 | 用途 |
|------|------|
| Next.js 14 (App Router) | React 框架 |
| TailwindCSS | 样式（Bloomberg Terminal 深色主题） |
| ECharts (echarts-for-react) | 9 种专业金融图表 |
| React Query (@tanstack/react-query) | 服务端状态管理 |
| Lucide React | 图标 |

### 前端性能优化

- ECharts 通过 `next/dynamic` + `ssr: false` 懒加载，仅使用图表的页面才加载 ECharts 包
- 集中化 ECharts 模块注册（`echarts-setup.ts`），避免重复注册
- 优化后各页面 First Load JS: ~91KB（优化前 323KB，降低 72%）

## API 端点

主要 API 端点：

```
GET  /api/data/sources          # 数据源列表
GET  /api/data/stocks           # 股票列表
GET  /api/data/stocks/{symbol}  # 股票历史数据
GET  /api/data/quality          # 数据质量评分
GET  /api/data/storage          # 存储使用统计

GET  /api/models/               # 模型列表
GET  /api/models/symbols        # 覆盖股票
GET  /api/models/compare        # 模型性能对比

GET  /api/backtest/             # 回测结果列表
GET  /api/backtest/summary      # 回测摘要
GET  /api/backtest/analysis     # 策略分析（含最佳模型推荐）
GET  /api/backtest/heatmap      # Sharpe 热力图数据
GET  /api/backtest/correlation  # 资产相关性矩阵
GET  /api/backtest/{id}/equity-curve  # 权益曲线

POST /api/data/sync             # 同步股票数据
```

完整 API 文档请访问 http://localhost:8000/api/docs

## 许可证

MIT License
