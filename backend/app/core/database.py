"""
数据库连接和初始化
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from datetime import datetime

from app.core.config import settings


# 创建异步引擎
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)

# 创建会话工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM基类"""
    pass


# ==================== 数据模型 ====================

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
    features = Column(JSON)  # 存储特征字典
    created_at = Column(DateTime, default=datetime.utcnow)


class MLModel(Base):
    """机器学习模型表"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # lstm, lightgbm, xgboost, ensemble
    version = Column(String(20))
    params = Column(JSON)
    metrics = Column(JSON)  # accuracy, precision, recall, f1, auc
    model_path = Column(String(500))
    status = Column(String(20), default="pending")  # pending, training, trained, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50))  # ml, technical, hybrid
    model_id = Column(Integer)  # 关联的模型ID
    params = Column(JSON)
    status = Column(String(20), default="inactive")  # inactive, active, backtesting
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
    metrics = Column(JSON)  # 详细指标
    equity_curve = Column(JSON)  # 权益曲线数据
    trades = Column(JSON)  # 交易记录
    created_at = Column(DateTime, default=datetime.utcnow)


class Trade(Base):
    """交易记录表"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, index=True)
    backtest_id = Column(Integer, index=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10))  # buy, sell
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
    level = Column(String(20))  # info, warning, danger
    title = Column(String(200))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 数据库初始化 ====================

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session() as session:
        yield session
