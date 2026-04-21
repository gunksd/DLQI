"""
数据库连接和初始化 — Supabase PostgreSQL + asyncpg
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from datetime import datetime
from loguru import logger

from app.core.config import settings


# Supabase PostgreSQL 连接（使用 asyncpg 驱动）
_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

try:
    engine = create_async_engine(
        _db_url, echo=False, pool_pre_ping=True,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"数据库连接配置失败: {e}，paper trading 功能不可用")
    engine = None
    async_session = None
    DB_AVAILABLE = False


class Base(DeclarativeBase):
    """ORM基类"""
    pass


# ==================== 原有数据模型 ====================

class StockData(Base):
    """股票数据表"""
    __tablename__ = "stock_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureData(Base):
    """特征数据表"""
    __tablename__ = "feature_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    features = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLModel(Base):
    """机器学习模型表"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)
    version = Column(String(20))
    params = Column(JSON)
    metrics = Column(JSON)
    model_path = Column(String(500))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50))
    model_id = Column(Integer)
    params = Column(JSON)
    status = Column(String(20), default="inactive")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    total_return = Column(Float)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    metrics = Column(JSON)
    equity_curve = Column(JSON)
    trades = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Trade(Base):
    """交易记录表"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, index=True)
    backtest_id = Column(Integer, index=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10))
    quantity = Column(Integer)
    price = Column(Float)
    commission = Column(Float)
    slippage = Column(Float)
    pnl = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RiskMetric(Base):
    """风险指标表"""
    __tablename__ = "risk_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, index=True)
    date = Column(DateTime, index=True, nullable=False)
    var_95 = Column(Float)
    var_99 = Column(Float)
    cvar_95 = Column(Float)
    volatility = Column(Float)
    beta = Column(Float)
    sharpe = Column(Float)
    max_drawdown = Column(Float)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """风险预警表"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, index=True)
    level = Column(String(20))
    title = Column(String(200))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 新增表：任务、模拟交易 ====================

class Job(Base):
    """异步任务表"""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    job_type = Column(String(50), nullable=False)      # train, backtest, sync
    status = Column(String(20), default="pending")     # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0)                # 0-100
    current_step = Column(String(200), default="")
    params = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperPortfolio(Base):
    """模拟交易组合"""
    __tablename__ = "paper_portfolios"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    initial_capital = Column(Float, default=100000)
    cash = Column(Float, default=100000)
    positions = Column(JSON, default=dict)             # {symbol: {qty, avg_price}}
    total_value = Column(Float, default=100000)
    model_id = Column(String(200))
    status = Column(String(20), default="active")      # active, closed
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperTrade(Base):
    """模拟交易记录"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(String(36), index=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)          # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0)
    signal_source = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)


# ==================== 数据库初始化 ====================

async def init_db():
    """初始化数据库（自动建表）"""
    global DB_AVAILABLE
    if not DB_AVAILABLE:
        logger.warning("数据库不可用，跳过初始化")
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Supabase PostgreSQL 数据库就绪")
    except Exception as e:
        logger.warning(f"数据库初始化失败: {e}，paper trading 功能不可用")
        DB_AVAILABLE = False


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    if not DB_AVAILABLE:
        raise RuntimeError("数据库不可用")
    async with async_session() as session:
        yield session
