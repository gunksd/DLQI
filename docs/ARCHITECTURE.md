# 基于机器学习的量化交易策略系统 - 系统架构设计

## 一、系统总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端展示层 (Frontend)                      │
│                  Next.js + TailwindCSS + ECharts                │
│                      Claymorphism 设计风格                        │
├─────────────────────────────────────────────────────────────────┤
│                         API 网关层                               │
│                    FastAPI + WebSocket                          │
├─────────────────────────────────────────────────────────────────┤
│                         业务逻辑层                               │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ 数据模块  │ 特征工程 │ 模型训练 │ 策略回测 │ 风控模块 │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
├─────────────────────────────────────────────────────────────────┤
│                         数据存储层                               │
│            PostgreSQL + Redis + HDF5 + MinIO                    │
└─────────────────────────────────────────────────────────────────┘
```

## 二、技术栈详细设计

### 2.1 后端技术栈

#### 核心框架
- **Python 3.11+**: 主要开发语言
- **FastAPI**: 高性能API框架，支持异步和WebSocket
- **Pydantic**: 数据验证和设置管理

#### 数据获取与处理
- **AKShare**: A 股行情数据源（日 K 线前/后复权）
- **pandas**: 数据处理核心库
- **numpy**: 数值计算
- **polars**: 高性能数据处理（可选）

#### 机器学习框架
- **scikit-learn**: 传统机器学习算法
- **LightGBM**: 梯度提升树模型
- **XGBoost**: 极端梯度提升
- **PyTorch**: 深度学习框架（LSTM/Transformer）
- **optuna**: 自动超参数优化

#### 量化交易库
- **backtrader**: 回测引擎
- **vectorbt**: 向量化回测
- **ta-lib**: 技术指标库
- **quantlib-python**: 金融工程库

#### 数据存储
- **PostgreSQL**: 结构化数据（交易记录、策略配置）
- **Redis**: 缓存层、实时数据
- **HDF5**: 时间序列数据高效存储
- **MinIO**: 对象存储（模型文件、图表）

### 2.2 前端技术栈

#### 核心框架
- **Next.js 14**: React全栈框架（App Router）
- **React 18**: 用户界面库
- **TypeScript**: 类型安全

#### 样式与UI
- **TailwindCSS**: 原子化CSS框架
- **shadcn/ui**: 高质量组件库
- **Framer Motion**: 动画库
- **Claymorphism**: 自定义3D软质UI风格

#### 数据可视化
- **ECharts**: 专业金融图表库（K线图、技术指标）
- **Recharts**: React图表库（备选）
- **TradingView Charting Library**: 专业行情图（可选）

#### 状态管理
- **Zustand**: 轻量级状态管理
- **React Query**: 服务端状态管理

#### 实时通信
- **Socket.IO Client**: WebSocket客户端
- **SWR**: 数据获取与缓存

## 三、系统模块详细设计

### 3.1 数据获取模块 (Data Module)

**职责**：
- 从多个数据源获取金融数据
- 数据清洗、对齐、标准化
- 增量更新与历史数据管理

**核心类**：
```python
class DataFetcher:
    - fetch_stock_data(symbol, start_date, end_date)
    - fetch_index_data()
    - fetch_financial_data()

class DataCleaner:
    - handle_missing_values()
    - detect_outliers()
    - align_timestamps()

class DataStorage:
    - save_to_hdf5()
    - save_to_postgresql()
    - update_incremental()
```

**数据字段标准**：
```python
{
    'symbol': str,          # 股票代码
    'date': datetime,       # 日期
    'open': float,          # 开盘价
    'high': float,          # 最高价
    'low': float,           # 最低价
    'close': float,         # 收盘价
    'volume': int,          # 成交量
    'amount': float,        # 成交额
    'turnover': float,      # 换手率
    'pct_change': float     # 涨跌幅
}
```

### 3.2 特征工程模块 (Feature Engineering)

**职责**：
- 构建技术指标特征
- 计算统计特征
- 特征选择与降维
- 特征标准化

**特征体系**：

#### A. 技术指标特征 (60+)
```python
class TechnicalIndicators:
    # 趋势指标
    - MA(periods=[5,10,20,60,120])
    - EMA(periods=[12,26])
    - MACD(fast=12, slow=26, signal=9)

    # 动量指标
    - RSI(period=14)
    - Stochastic(K=14, D=3)
    - Williams_R(period=14)

    # 波动率指标
    - Bollinger_Bands(period=20, std=2)
    - ATR(period=14)
    - Keltner_Channel()

    # 成交量指标
    - OBV()
    - VWAP()
    - Chaikin_Money_Flow()
```

#### B. 统计特征 (30+)
```python
class StatisticalFeatures:
    - rolling_return(windows=[5,10,20])
    - rolling_volatility(windows=[20,60])
    - rolling_skewness(window=60)
    - rolling_kurtosis(window=60)
    - sharpe_ratio(window=252)
    - max_drawdown(window=252)
```

#### C. 因子特征
```python
class FactorFeatures:
    # 价值因子
    - PE_ratio
    - PB_ratio
    - PS_ratio

    # 成长因子
    - revenue_growth
    - profit_growth

    # 质量因子
    - ROE
    - ROA
    - debt_ratio
```

#### D. 特征选择
```python
class FeatureSelector:
    - correlation_filter(threshold=0.95)
    - variance_threshold(threshold=0.01)
    - mutual_information_selection(k=50)
    - recursive_feature_elimination()
    - SHAP_importance()
```

### 3.3 模型训练模块 (Model Training)

**模型集成架构**：

```python
class ModelFactory:
    models = {
        'lstm': LSTMModel,
        'transformer': TransformerModel,
        'lightgbm': LightGBMModel,
        'xgboost': XGBoostModel,
        'random_forest': RandomForestModel,
        'ensemble': EnsembleModel
    }
```

#### A. LSTM 模型
```python
class LSTMModel:
    architecture:
        - Input(seq_length=60, features=100)
        - LSTM(128, return_sequences=True, dropout=0.2)
        - LSTM(64, dropout=0.2)
        - Dense(32, activation='relu')
        - Dropout(0.3)
        - Dense(1, activation='linear')

    training:
        - optimizer: Adam(lr=0.001)
        - loss: MSE
        - batch_size: 64
        - epochs: 100
        - early_stopping: patience=10
```

#### B. Transformer 模型
```python
class TransformerModel:
    architecture:
        - PositionalEncoding(d_model=128)
        - TransformerEncoder(
            num_layers=4,
            d_model=128,
            num_heads=8,
            dim_feedforward=512,
            dropout=0.1
        )
        - Dense(1)
```

#### C. LightGBM 模型
```python
class LightGBMModel:
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1
    }
```

#### D. 集成学习
```python
class EnsembleModel:
    method: 'stacking'
    base_models: [LSTM, LightGBM, XGBoost]
    meta_model: Ridge(alpha=1.0)
    weights: [0.3, 0.4, 0.3]
```

**训练流程**：
```python
class TrainingPipeline:
    1. 数据分割
       - train: 70%
       - validation: 15%
       - test: 15%

    2. 时间序列交叉验证
       - TimeSeriesSplit(n_splits=5)
       - WalkForwardValidation

    3. 超参数优化
       - Optuna TPESampler
       - n_trials: 100

    4. 模型评估
       - MSE, MAE, R²
       - Directional Accuracy
       - IC (信息系数)
```

### 3.4 策略生成模块 (Strategy Generation)

**策略类型**：

#### A. 信号生成策略
```python
class SignalGenerator:
    def generate_signal(prediction, threshold=0.02):
        if prediction > threshold:
            return 1  # 买入信号
        elif prediction < -threshold:
            return -1  # 卖出信号
        else:
            return 0  # 持有
```

#### B. 多空策略
```python
class LongShortStrategy:
    - long_threshold: 0.02
    - short_threshold: -0.02
    - position_size: dynamic (based on confidence)
    - rebalance_frequency: daily
```

#### C. 仓位管理策略
```python
class PositionManager:
    methods = {
        'fixed': 固定仓位(0.3),
        'kelly': Kelly公式计算最优仓位,
        'risk_parity': 风险平价配置,
        'volatility_targeting': 波动率目标
    }
```

### 3.5 回测系统 (Backtesting)

**回测引擎**：
```python
class BacktestEngine:
    initial_capital: 1,000,000
    commission: 0.0003  # 万三
    slippage: 0.001     # 0.1%

    def run_backtest():
        1. 初始化账户
        2. 遍历历史数据
        3. 生成交易信号
        4. 执行交易（考虑成本）
        5. 更新持仓和资金
        6. 记录交易日志
        7. 计算绩效指标
```

**绩效指标**：
```python
class PerformanceMetrics:
    # 收益指标
    - total_return
    - annual_return
    - cumulative_return
    - daily_return

    # 风险指标
    - volatility (年化波动率)
    - max_drawdown (最大回撤)
    - max_drawdown_duration

    # 风险调整收益
    - sharpe_ratio (夏普比率)
    - sortino_ratio
    - calmar_ratio
    - omega_ratio

    # 交易指标
    - win_rate (胜率)
    - profit_factor
    - average_win / average_loss
    - total_trades

    # 基准对比
    - alpha (超额收益)
    - beta (系统性风险)
    - information_ratio
    - tracking_error
```

### 3.6 风控模块 (Risk Management)

**风险度量**：
```python
class RiskMetrics:
    # VaR计算
    def calculate_VaR(returns, confidence=0.95):
        - historical_VaR
        - parametric_VaR
        - monte_carlo_VaR

    # CVaR (条件风险价值)
    def calculate_CVaR(returns, confidence=0.95)

    # 压力测试
    def stress_test(scenarios)
```

**风控规则**：
```python
class RiskControl:
    limits = {
        'max_position_size': 0.2,      # 单只股票最大仓位
        'max_drawdown_limit': 0.15,    # 最大回撤限制
        'max_leverage': 1.0,           # 最大杠杆
        'max_sector_exposure': 0.4     # 行业暴露限制
    }

    def apply_stop_loss(position, price):
        if loss > max_loss_threshold:
            close_position()

    def apply_take_profit(position, price):
        if profit > take_profit_threshold:
            close_position()
```

## 四、数据流设计

### 4.1 离线训练流程
```
原始数据
  → 数据清洗
  → 特征工程
  → 模型训练
  → 模型评估
  → 模型保存
```

### 4.2 在线预测流程
```
实时行情
  → 特征计算
  → 模型预测
  → 信号生成
  → 风控检查
  → 交易执行
  → 结果记录
```

### 4.3 回测流程
```
历史数据
  → 加载模型
  → 信号生成
  → 模拟交易
  → 绩效计算
  → 结果可视化
```

## 五、API 接口设计

### 5.1 RESTful API

```python
# 数据管理
GET    /api/data/stocks              # 获取股票列表
GET    /api/data/stocks/{symbol}     # 获取单只股票数据
POST   /api/data/update              # 更新数据

# 特征工程
GET    /api/features/list            # 获取特征列表
POST   /api/features/calculate       # 计算特征
GET    /api/features/importance      # 特征重要性

# 模型管理
GET    /api/models/list              # 获取模型列表
POST   /api/models/train             # 训练模型
GET    /api/models/{id}/metrics      # 获取模型指标
POST   /api/models/{id}/predict      # 模型预测

# 策略回测
POST   /api/backtest/run             # 运行回测
GET    /api/backtest/{id}/results    # 获取回测结果
GET    /api/backtest/{id}/trades     # 获取交易记录

# 风险管理
GET    /api/risk/metrics             # 风险指标
GET    /api/risk/var                 # VaR计算
POST   /api/risk/stress-test         # 压力测试
```

### 5.2 WebSocket API

```python
# 实时数据推送
ws://api/stream/market/{symbol}      # 实时行情
ws://api/stream/signals              # 实时交易信号
ws://api/stream/portfolio            # 实时持仓
ws://api/stream/trades               # 实时成交
```

## 六、数据库设计

### 6.1 PostgreSQL 表结构

```sql
-- 股票基本信息表
CREATE TABLE stocks (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    exchange VARCHAR(20),
    sector VARCHAR(50),
    industry VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 策略配置表
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    model_type VARCHAR(50),
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 回测结果表
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(15,2),
    final_value DECIMAL(15,2),
    total_return DECIMAL(10,4),
    annual_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    win_rate DECIMAL(10,4),
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 交易记录表
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtest_results(id),
    symbol VARCHAR(20),
    trade_date DATE,
    action VARCHAR(10),  -- BUY/SELL
    price DECIMAL(10,2),
    quantity INTEGER,
    amount DECIMAL(15,2),
    commission DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型表
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    model_type VARCHAR(50),
    version VARCHAR(20),
    hyperparameters JSONB,
    training_metrics JSONB,
    model_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 Redis 缓存策略

```python
# 缓存键设计
cache_keys = {
    'market_data': 'market:{symbol}:{date}',      # TTL: 1天
    'features': 'features:{symbol}:{date}',       # TTL: 1天
    'predictions': 'pred:{model}:{symbol}',       # TTL: 1小时
    'signals': 'signal:{strategy}:{symbol}',      # TTL: 1小时
    'portfolio': 'portfolio:{user_id}',           # TTL: 实时更新
}
```

### 6.3 HDF5 文件结构

```python
# 时间序列数据存储
hdf5_structure = {
    '/market_data/{symbol}': {
        'columns': ['open', 'high', 'low', 'close', 'volume'],
        'index': 'date',
        'compression': 'gzip',
        'compression_level': 9
    },
    '/features/{symbol}': {
        'columns': ['feature_1', 'feature_2', ..., 'feature_n'],
        'index': 'date'
    },
    '/predictions/{model}/{symbol}': {
        'columns': ['prediction', 'confidence'],
        'index': 'date'
    }
}
```

## 七、部署方案

### 7.1 开发环境
```yaml
backend:
  - Python 3.11
  - Poetry (依赖管理)
  - pytest (测试)
  - black + ruff (代码格式化)

frontend:
  - Node.js 20
  - pnpm (包管理)
  - ESLint + Prettier
  - Jest (测试)

database:
  - PostgreSQL 16 (Docker)
  - Redis 7 (Docker)
  - MinIO (Docker)
```

### 7.2 生产环境
```yaml
架构: 微服务 + 容器化

services:
  - api_gateway: Nginx
  - backend_api: FastAPI (Gunicorn + Uvicorn)
  - frontend: Next.js (Static Export / SSR)
  - database: PostgreSQL (主从复制)
  - cache: Redis (哨兵模式)
  - storage: MinIO (分布式存储)
  - monitoring: Prometheus + Grafana
  - logging: ELK Stack
```

### 7.3 Docker Compose
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: quant_trading
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - minio
    environment:
      DATABASE_URL: postgresql://admin:password@postgres:5432/quant_trading
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

## 八、性能优化策略

### 8.1 后端优化
- 使用异步IO (async/await)
- 数据库连接池
- Redis缓存热点数据
- 批量数据操作
- 特征计算并行化
- 模型推理优化 (ONNX Runtime)

### 8.2 前端优化
- 代码分割 (Code Splitting)
- 懒加载 (Lazy Loading)
- 虚拟滚动 (Virtual Scrolling)
- 图表按需渲染
- WebSocket增量更新
- Service Worker缓存

### 8.3 数据库优化
- 索引优化
- 分区表 (按时间分区)
- 物化视图
- 查询优化
- 读写分离

## 九、安全设计

### 9.1 认证授权
- JWT Token认证
- OAuth 2.0集成
- 基于角色的访问控制 (RBAC)
- API密钥管理

### 9.2 数据安全
- 数据加密 (传输 + 存储)
- SQL注入防护
- XSS防护
- CSRF防护
- 敏感信息脱敏

### 9.3 系统安全
- HTTPS强制
- 请求限流
- 异常检测
- 审计日志
- 备份恢复

## 十、监控与日志

### 10.1 监控指标
```python
business_metrics = {
    '策略性能': ['收益率', '夏普比率', '最大回撤'],
    '交易指标': ['交易次数', '胜率', '平均盈亏'],
    '风险指标': ['VaR', '波动率', '仓位暴露']
}

technical_metrics = {
    'API性能': ['响应时间', 'QPS', '错误率'],
    '系统资源': ['CPU', '内存', '磁盘', '网络'],
    '数据库': ['连接数', '慢查询', '死锁'],
    '缓存': ['命中率', '内存使用', '过期键']
}
```

### 10.2 日志规范
```python
log_levels = {
    'DEBUG': '调试信息',
    'INFO': '关键业务流程',
    'WARNING': '警告信息',
    'ERROR': '错误信息',
    'CRITICAL': '严重错误'
}

log_format = {
    'timestamp': 'ISO8601格式',
    'level': '日志级别',
    'service': '服务名称',
    'trace_id': '链路追踪ID',
    'message': '日志内容',
    'extra': '附加信息'
}
```

## 十一、测试策略

### 11.1 单元测试
- 覆盖率目标: 80%+
- 关键模块: 100%覆盖
- 工具: pytest + pytest-cov

### 11.2 集成测试
- API接口测试
- 数据库集成测试
- 第三方服务Mock

### 11.3 性能测试
- 负载测试 (Locust)
- 压力测试
- 并发测试

### 11.4 回测验证
- 样本外测试
- 不同市场周期
- 参数敏感性分析
- 蒙特卡洛模拟

## 十二、项目里程碑

```
Phase 1: 基础架构搭建 (Week 1-2)
  - 项目初始化
  - 数据库设计
  - API框架搭建
  - 前端框架搭建

Phase 2: 数据与特征 (Week 3-4)
  - 数据获取模块
  - 数据清洗
  - 特征工程
  - 特征选择

Phase 3: 模型开发 (Week 5-7)
  - LSTM模型
  - LightGBM模型
  - 模型集成
  - 超参数优化

Phase 4: 策略与回测 (Week 8-9)
  - 策略生成
  - 回测引擎
  - 绩效分析
  - 风控模块

Phase 5: 前端开发 (Week 10-11)
  - UI设计实现
  - 数据可视化
  - 实时更新
  - 交互优化

Phase 6: 测试与优化 (Week 12)
  - 功能测试
  - 性能优化
  - 文档完善
  - 部署上线

Phase 7: 论文撰写 (Week 13-14)
  - 开题报告
  - 论文初稿
  - 实验结果
  - 答辩准备
```

## 十三、技术亮点与创新点

1. **多模型集成**: LSTM + LightGBM + XGBoost 融合
2. **自适应特征选择**: 基于SHAP的动态特征筛选
3. **实时风控**: VaR + 动态止损的双重保护
4. **可解释性**: SHAP值分析模型决策
5. **高性能回测**: 向量化计算，支持大规模回测
6. **现代化UI**: Claymorphism设计风格
7. **实时交互**: WebSocket实时数据推送
8. **可扩展架构**: 微服务 + 容器化部署

---

**文档版本**: v1.0
**创建时间**: 2025-01
**维护者**: 毕业设计团队
