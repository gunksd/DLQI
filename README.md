# DLQI — 基于深度学习的 A 股量化投资研究平台

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-4fc08d.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> DLQI 是一个端到端的 A 股量化交易研究平台，以**多股联合训练的 Transformer 分类器**为主角模型，对 5 只代表性 A 股（贵州茅台 600519、中国平安 601318、招商银行 600036、宁德时代 300750、比亚迪 002594）进行方向预测与策略回测，支持 LightGBM / XGBoost / BiLSTM+Attention 基线对照。数据源 AKShare（后复权日线，10 年历史）。

## 技术栈

**后端**：FastAPI · SQLAlchemy async · asyncpg · Supabase PostgreSQL
**前端**：Vue 3 · TypeScript · Vite · Vue Router 4 · Pinia · ECharts · Tailwind CSS 3
**建模**：PyTorch（Transformer / BiLSTM）· LightGBM · XGBoost · scikit-learn
**数据**：AKShare（A 股前/后复权日线）

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│    前端 Vue 3 + Vite + ECharts (Bloomberg Terminal 暗色)    │
├─────────────────────────────────────────────────────────────┤
│           REST API (FastAPI + Uvicorn · /api)               │
├─────────┬─────────┬──────────┬──────────┬───────────────────┤
│ data    │ models  │ backtest │ risk     │ paper_trading     │
├─────────┴─────────┴──────────┴──────────┴───────────────────┤
│  AKShare · 本地 CSV · SQLite · 训练模型权重 · 回测曲线 JSON │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.12
- Node.js 20+

### 安装

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 前端
cd ../frontend-vue
npm install
```

### 启动

```bash
# 终端 1 — 后端（:8000）
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# 终端 2 — 前端（:5173）
cd frontend-vue
npm run dev
```

| 服务 | URL |
|------|-----|
| 前端仪表盘 | http://localhost:5173 |
| API 文档（Swagger） | http://localhost:8000/api/docs |
| API 文档（ReDoc） | http://localhost:8000/api/redoc |

### 数据拉取与模型训练

```bash
# 拉取 5 只 A 股 10 年历史（AKShare，hfq 后复权）
backend/venv/bin/python scripts/fetch_cn_data.py

# 训练全部基线模型（LightGBM/XGBoost/LSTM + Transformer MULTI）
backend/venv/bin/python scripts/train_cn_models.py

# 训练冠军专用 Transformer（24 维特征 + 决策阈值学习 + 超参搜索）
backend/venv/bin/python scripts/train_champion.py

# 回测 + 最佳模型分析
backend/venv/bin/python scripts/run_pipeline.py
```

## 项目结构

```
DLQI/
├── backend/                   # FastAPI
│   ├── main.py
│   ├── app/
│   │   ├── api/               # data / models / backtest / risk / jobs / paper_trading
│   │   ├── core/              # config.py / database.py
│   │   ├── models/            # SQLAlchemy ORM
│   │   └── services/          # 业务逻辑（训练、回测、模拟交易、风控）
│   └── requirements.txt
├── frontend-vue/              # Vue 3
│   └── src/
│       ├── views/             # 8 个页面组件
│       ├── components/layout/AppLayout.vue
│       ├── composables/api.ts
│       ├── stores/            # Pinia
│       └── types/
├── data/
│   ├── raw/                   # cn_{symbol}.csv (AKShare hfq)
│   └── models/                # 训练好的模型（每个一个目录）
├── scripts/
│   ├── fetch_cn_data.py
│   ├── train_cn_models.py     # 基线多模型训练
│   ├── train_champion.py      # 冠军 Transformer 训练
│   └── run_pipeline.py        # 回测 + 分析
├── results/
│   ├── backtest_results.csv
│   ├── model_analysis.json    # 冠军 + 排行榜 + 按类型汇总
│   ├── ablation.csv           # 冠军消融实验结果
│   └── equity_curves/         # 每个模型的资金曲线 JSON
└── paper_outline.md           # 论文大纲（围绕冠军模型组织）
```

## 前端页面

| 路由 | 视图 | 功能 |
|------|------|------|
| `/` | DashboardView | 总览仪表盘 |
| `/strategies` | StrategiesView | 策略管理 |
| `/models` | ModelsView | 模型列表与特征重要性 |
| `/backtest` | BacktestView | 回测结果与权益曲线 |
| `/trading` | TradingView | 模拟交易 |
| `/risk` | RiskView | 风险监控（VaR / 压力测试 / 沪深300 相关性） |
| `/data` | DataView | 数据管理 |
| `/tuning` | TuningView | 模型调参 |

## 主要 API 端点

```
# 数据
GET  /api/data/sources             数据源状态
GET  /api/data/stocks              股票列表
GET  /api/data/stocks/{symbol}     单只 K 线
GET  /api/data/history             /stocks/{symbol} 的 query-string 别名
POST /api/data/sync                异步触发 AKShare 同步
GET  /api/data/quality             数据质量
GET  /api/data/storage             存储统计

# 模型
GET  /api/models/                  模型列表
GET  /api/models/{id}              模型详情
GET  /api/models/{id}/predictions  预测值
GET  /api/models/{id}/feature-importance
POST /api/models/train             单股单模型训练
POST /api/models/train-multi       多股联合训练

# 回测
GET  /api/backtest/                回测结果列表
GET  /api/backtest/{id}/equity-curve
GET  /api/backtest/correlation     资产相关性矩阵
POST /api/backtest/run             触发完整 pipeline
GET  /api/backtest/recommend       最佳策略推荐

# 风险
GET  /api/risk/overview
GET  /api/risk/var
GET  /api/risk/alerts
POST /api/risk/stress-test

# 模拟交易
POST /api/paper-trading/portfolios
POST /api/paper-trading/portfolios/from-strategy
POST /api/paper-trading/portfolios/{id}/run
```

完整 API 文档：http://localhost:8000/api/docs

## A 股适配要点

- **后复权（hfq）**：AKShare 前复权（qfq）对长历史会产生负价格（茅台 2016 起 100+ 天），训练特征（收益率 / RSI / MACD）会被污染。项目全栈使用 hfq。
- **T+1**：回测引擎强制买入当日不能卖出。
- **非对称费率**：买入 = 佣金万2.5 + 滑点 0.1%；卖出 = 佣金万2.5 + 印花税 0.05% + 滑点 0.1%。
- **基准**：相关性 / 超额收益对比基准为**沪深300（000300）**。

## 冠军模型（本项目核心）

**多股联合 Transformer 分类器** — 将 5 只股票的历史数据在时序对齐后联合训练，使 Transformer 学会**跨股票可迁移的短期方向模式**，而不是在每只股票 ~2500 条样本上单独训练（容易过拟合）。

训练侧关键设计：
1. **时序安全切分**：按时间顺序 train/val/test = 70/15/15，不跨时间 shuffle，杜绝数据泄漏
2. **24 维特征**：在 OHLCV+收益率+MA+波动率+RSI+MACD 基础上加布林带、KDJ、ADX、OBV、ATR、量比等
3. **决策阈值学习 τ\***：在验证集上按 F1 最大化学到的阈值，替代简单的 `pred > 0`
4. **置信度过滤**：softmax 预测上涨概率 < 0.55 不开仓，降低噪声交易

完整消融实验见 `results/ablation.csv`，论文叙事见 `paper_outline.md`。

## 许可证

MIT License
