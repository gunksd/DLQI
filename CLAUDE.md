# DLQI — Claude Code 项目指南

## 项目概述

DLQI（Deep Learning Quantitative Intelligence）是一个量化交易研究平台，用于毕业论文研究。
使用深度学习模型（LSTM、Transformer、LightGBM、XGBoost）对 5 只 A 股（贵州茅台、中国平安、招商银行、宁德时代、比亚迪）进行预测和回测。
数据源：AKShare（A 股前复权日线，10 年历史数据）。

**单用户本地使用，无需认证。**

## 技术栈

- **后端**: FastAPI + SQLAlchemy (async) + asyncpg → Supabase PostgreSQL
- **前端**: Vue 3 + TypeScript + Vite + Vue Router 4 + Pinia + ECharts + Tailwind CSS 3
- **ML**: LightGBM、XGBoost、LSTM（PyTorch）
- **数据库**: Supabase PostgreSQL（云端）

## 目录结构

```
DLQI/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/      # 路由：backtest, data, models, risk, paper_trading, jobs
│   │   ├── core/     # config.py, database.py
│   │   ├── models/   # SQLAlchemy ORM 模型
│   │   └── services/ # 业务逻辑服务
│   ├── main.py
│   ├── .env          # DATABASE_URL（不提交）
│   └── requirements.txt
├── frontend-vue/     # Vue 3 前端
│   ├── src/
│   │   ├── views/    # 8 个页面组件
│   │   ├── components/layout/AppLayout.vue
│   │   ├── composables/api.ts  # Axios API 封装
│   │   ├── stores/   # Pinia stores
│   │   ├── router/   # Vue Router
│   │   └── types/    # TypeScript 类型定义
│   └── vite.config.ts  # /api → http://localhost:8000 代理
├── data/             # 股票数据、训练好的模型
└── docs/             # 项目文档
```

## 开发命令

```bash
# 后端
cd backend && uvicorn main:app --reload --port 8000

# 前端
cd frontend-vue && npm run dev   # http://localhost:5173
cd frontend-vue && npm run build # 生产构建
```

## 环境变量

`backend/.env`:
```
DATABASE_URL=postgresql://postgres:PASSWORD@db.dmiuanoxqekxonwtvlsw.supabase.co:5432/postgres
```

## API 路由

| 前缀 | 功能 |
|------|------|
| `/api/data` | 股票数据管理 |
| `/api/models` | ML 模型管理 |
| `/api/backtest` | 回测执行与结果 |
| `/api/risk` | 风险监控与 VaR |
| `/api/paper-trading` | 模拟交易 |
| `/api/jobs` | 后台任务状态 |

## 前端页面

| 路由 | 视图 | 功能 |
|------|------|------|
| `/` | DashboardView | 总览仪表盘 |
| `/strategies` | StrategiesView | 策略管理 |
| `/models` | ModelsView | 模型列表与特征重要性 |
| `/backtest` | BacktestView | 回测结果与权益曲线 |
| `/trading` | TradingView | 模拟交易 |
| `/risk` | RiskView | 风险监控 |
| `/data` | DataView | 数据管理 |
| `/tuning` | TuningView | 模型调参 |

## 设计规范

- Bloomberg Terminal 暗色主题
- 主色：`#0a0a0a` 背景，`#3b82f6` 强调色
- 盈利：`#10b981`（gain），亏损：`#ef4444`（loss）
- 组件类：`.t-card`、`.t-btn-primary`、`.t-btn-ghost`、`.t-badge`、`.t-table`

## 注意事项

- TypeScript strict 模式开启，可选字段需用 `?? 0` 处理
- API 响应通过 axios 拦截器自动解包 `res.data`
- `ModelInfo` 的回测指标字段（sharpe_ratio 等）为可选，来自后端 metrics 字段展开
