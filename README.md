# 🚀 基于机器学习的量化交易策略系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 一个完整的量化交易研究平台,集成机器学习模型、策略回测和风险管理功能。

## ✨ 项目特色

- 🤖 **多模型集成**: LSTM、Transformer、LightGBM、XGBoost
- 📊 **专业回测**: 完整的策略回测引擎,支持交易成本和滑点模拟
- 🛡️ **风险管理**: VaR/CVaR计算、动态止损、仓位控制
- 🎨 **现代UI**: Next.js + Claymorphism 设计风格
- 📈 **实时可视化**: ECharts金融图表,WebSocket实时更新
- 🔧 **高可扩展**: 微服务架构,容器化部署

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    前端层 (Next.js + TailwindCSS)                │
├─────────────────────────────────────────────────────────────────┤
│                    API网关 (FastAPI + WebSocket)                 │
├─────────────────────────────────────────────────────────────────┤
│    数据模块  │  特征工程  │  模型训练  │  策略回测  │  风控模块  │
├─────────────────────────────────────────────────────────────────┤
│            PostgreSQL + Redis + HDF5 + MinIO                    │
└─────────────────────────────────────────────────────────────────┘
```

详细架构文档: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📁 项目结构

```
DLQI/
├── backend/              # Python后端
│   ├── app/
│   │   ├── api/         # API路由
│   │   ├── models/      # 机器学习模型
│   │   ├── services/    # 业务逻辑
│   │   └── utils/       # 工具函数
│   └── tests/           # 测试
├── frontend/            # Next.js前端
│   └── src/
│       ├── app/         # 页面路由
│       ├── components/  # React组件
│       └── lib/         # 工具库
├── data/                # 数据存储
│   ├── raw/            # 原始数据
│   ├── processed/      # 处理后数据
│   ├── features/       # 特征数据
│   └── models/         # 训练模型
├── docs/               # 文档
├── scripts/            # 脚本
└── config/             # 配置文件
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- PostgreSQL 16
- Redis 7

### 后端安装

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 前端安装

```bash
cd frontend
pnpm install  # 或 npm install
```

### 使用Docker Compose (推荐)

```bash
docker-compose up -d
```

访问:
- 前端: http://localhost:3000
- API文档: http://localhost:8000/docs
- MinIO控制台: http://localhost:9001

## 📖 使用指南

### 1. 数据获取

```bash
python scripts/data_collection/fetch_stock_data.py --symbol AAPL --start 2020-01-01
```

### 2. 特征工程

```bash
python scripts/model_training/generate_features.py --input data/raw --output data/features
```

### 3. 模型训练

```bash
python scripts/model_training/train_lstm.py --config config/lstm_config.yaml
```

### 4. 策略回测

```bash
python scripts/backtest/run_backtest.py --strategy lstm_long_short --start 2023-01-01
```

### 5. 启动前端

```bash
cd frontend
pnpm dev
```

## 🎯 核心功能

### 数据模块
- ✅ 多数据源集成 (Tushare, Yahoo Finance)
- ✅ 数据清洗与预处理
- ✅ 增量更新机制

### 特征工程
- ✅ 60+ 技术指标 (MA, RSI, MACD, Bollinger Bands...)
- ✅ 30+ 统计特征 (收益率, 波动率, 偏度, 峰度...)
- ✅ 特征选择 (相关性过滤, PCA, SHAP)

### 机器学习模型
- ✅ LSTM深度学习模型
- ✅ Transformer时间序列模型
- ✅ LightGBM梯度提升
- ✅ XGBoost极端梯度提升
- ✅ 模型集成 (Stacking)
- ✅ 超参数优化 (Optuna)

### 策略回测
- ✅ 多空策略支持
- ✅ 仓位管理 (固定仓位, Kelly公式, 风险平价)
- ✅ 交易成本模拟
- ✅ 滑点处理
- ✅ 绩效指标 (夏普比率, 最大回撤, 胜率...)

### 风险管理
- ✅ VaR/CVaR计算
- ✅ 动态止损
- ✅ 仓位暴露控制
- ✅ 压力测试

### 前端可视化
- ✅ Claymorphism设计风格
- ✅ K线图与交易信号
- ✅ 收益曲线与回撤分析
- ✅ 模型性能对比
- ✅ 实时数据推送

## 📊 性能指标

基于历史数据回测结果 (2020-2024):

| 指标 | 值 |
|------|-----|
| 年化收益率 | 18.5% |
| 夏普比率 | 1.42 |
| 最大回撤 | -12.3% |
| 胜率 | 56.8% |
| 交易次数 | 342 |

## 🛠️ 技术栈

### 后端
- FastAPI - Web框架
- PyTorch - 深度学习
- LightGBM / XGBoost - 梯度提升
- Pandas / NumPy - 数据处理
- TA-Lib - 技术指标
- Backtrader - 回测引擎

### 前端
- Next.js 14 - React框架
- TailwindCSS - CSS框架
- shadcn/ui - 组件库
- ECharts - 图表库
- Zustand - 状态管理
- Socket.IO - 实时通信

### 数据库
- PostgreSQL - 关系数据库
- Redis - 缓存
- HDF5 - 时间序列存储
- MinIO - 对象存储

## 📝 论文相关

本项目作为毕业设计的一部分,相关论文材料位于:

- 开题报告: [docs/thesis/opening_report.md](docs/thesis/opening_report.md)
- 论文初稿: [docs/thesis/thesis_draft.md](docs/thesis/thesis_draft.md)
- 实验结果: [docs/thesis/experiment_results.md](docs/thesis/experiment_results.md)

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

## 📄 许可证

MIT License

## 👥 作者

毕业设计项目 - 2025

## 🔗 相关资源

- [系统架构文档](docs/ARCHITECTURE.md)
- [API文档](http://localhost:8000/docs)
- [用户指南](docs/user_guide/)

---

⭐ 如果这个项目对你有帮助,请给一个Star!
