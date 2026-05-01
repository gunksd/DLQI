"""
策略管理 API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random

router = APIRouter()


# ==================== 请求/响应模型 ====================

class StrategyConfig(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str  # ml, technical, hybrid
    model_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SignalRequest(BaseModel):
    symbol: str
    date: Optional[str] = None


# ==================== 模拟数据 ====================

MOCK_STRATEGIES = [
    {
        "id": 1,
        "name": "ML集成策略",
        "description": "基于LSTM+LightGBM集成模型的量化策略",
        "strategy_type": "ml",
        "model_id": 5,
        "params": {
            "threshold": 0.6,
            "holding_period": 5,
            "max_positions": 10,
            "position_size": 0.1
        },
        "status": "active",
        "performance": {
            "total_return": 0.185,
            "sharpe_ratio": 1.42,
            "max_drawdown": -0.123,
            "win_rate": 0.58
        },
        "created_at": datetime.now() - timedelta(days=30),
        "updated_at": datetime.now()
    },
    {
        "id": 2,
        "name": "动量反转策略",
        "description": "结合短期动量和长期反转的技术分析策略",
        "strategy_type": "technical",
        "model_id": None,
        "params": {
            "momentum_window": 20,
            "reversal_window": 60,
            "rsi_oversold": 30,
            "rsi_overbought": 70
        },
        "status": "active",
        "performance": {
            "total_return": 0.142,
            "sharpe_ratio": 1.15,
            "max_drawdown": -0.156,
            "win_rate": 0.52
        },
        "created_at": datetime.now() - timedelta(days=60),
        "updated_at": datetime.now() - timedelta(days=5)
    },
    {
        "id": 3,
        "name": "混合策略Alpha",
        "description": "ML信号与技术指标结合的混合策略",
        "strategy_type": "hybrid",
        "model_id": 1,
        "params": {
            "ml_weight": 0.6,
            "technical_weight": 0.4,
            "entry_threshold": 0.65,
            "exit_threshold": 0.45
        },
        "status": "backtesting",
        "performance": {
            "total_return": 0.168,
            "sharpe_ratio": 1.35,
            "max_drawdown": -0.135,
            "win_rate": 0.55
        },
        "created_at": datetime.now() - timedelta(days=15),
        "updated_at": datetime.now() - timedelta(days=1)
    },
    {
        "id": 4,
        "name": "趋势跟踪策略",
        "description": "基于均线系统的趋势跟踪策略",
        "strategy_type": "technical",
        "model_id": None,
        "params": {
            "fast_ma": 5,
            "slow_ma": 20,
            "signal_ma": 60,
            "atr_multiplier": 2.0
        },
        "status": "inactive",
        "performance": {
            "total_return": 0.098,
            "sharpe_ratio": 0.85,
            "max_drawdown": -0.198,
            "win_rate": 0.48
        },
        "created_at": datetime.now() - timedelta(days=90),
        "updated_at": datetime.now() - timedelta(days=30)
    }
]


# ==================== API端点 ====================

@router.get("/")
async def get_strategies(
    status: Optional[str] = None,
    strategy_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取策略列表"""
    strategies = MOCK_STRATEGIES.copy()

    if status:
        strategies = [s for s in strategies if s["status"] == status]
    if strategy_type:
        strategies = [s for s in strategies if s["strategy_type"] == strategy_type]

    return {
        "items": strategies,
        "total": len(strategies),
        "page": page,
        "page_size": page_size
    }


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int):
    """获取单个策略详情"""
    for strategy in MOCK_STRATEGIES:
        if strategy["id"] == strategy_id:
            return strategy
    raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 未找到")


@router.post("/")
async def create_strategy(config: StrategyConfig):
    """创建新策略"""
    new_strategy = {
        "id": len(MOCK_STRATEGIES) + 1,
        "name": config.name,
        "description": config.description,
        "strategy_type": config.strategy_type,
        "model_id": config.model_id,
        "params": config.params or {},
        "status": "inactive",
        "performance": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    return {"message": "策略创建成功", "strategy": new_strategy}


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: int, request: StrategyUpdateRequest):
    """更新策略"""
    for strategy in MOCK_STRATEGIES:
        if strategy["id"] == strategy_id:
            if request.name:
                strategy["name"] = request.name
            if request.description:
                strategy["description"] = request.description
            if request.params:
                strategy["params"].update(request.params)
            if request.status:
                strategy["status"] = request.status
            strategy["updated_at"] = datetime.now()
            return {"message": "策略更新成功", "strategy": strategy}

    raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 未找到")


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int):
    """删除策略"""
    return {"message": f"策略 {strategy_id} 已删除"}


@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: int):
    """激活策略"""
    return {
        "message": f"策略 {strategy_id} 已激活",
        "status": "active"
    }


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: int):
    """停用策略"""
    return {
        "message": f"策略 {strategy_id} 已停用",
        "status": "inactive"
    }


@router.get("/{strategy_id}/signals")
async def get_strategy_signals(
    strategy_id: int,
    symbol: str = "600519",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """获取策略信号"""
    # 真实价格范围映射
    price_map = {"600519": 1385, "601318": 59, "600036": 38, "300750": 436, "002594": 103}
    base_price = price_map.get(symbol, 100)

    signals = []
    base_date = datetime.now()

    for i in range(limit):
        date = base_date - timedelta(days=i)
        signal_type = random.choice(["buy", "sell", "hold"])
        confidence = random.uniform(0.5, 0.95)

        if signal_type != "hold":
            signals.append({
                "date": date.strftime("%Y-%m-%d"),
                "symbol": symbol,
                "signal": signal_type,
                "confidence": round(confidence, 4),
                "price": round(base_price * (1 + random.uniform(-0.03, 0.03)), 2),
                "indicators": {
                    "rsi": round(random.uniform(20, 80), 2),
                    "macd": round(random.uniform(-2, 2), 4),
                    "ma_cross": random.choice(["golden", "death", "none"])
                }
            })

    return {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "signals": signals[:50],  # 只返回非hold信号
        "total": len(signals)
    }


@router.get("/{strategy_id}/positions")
async def get_strategy_positions(strategy_id: int):
    """获取当前持仓"""
    positions = [
        {
            "symbol": "600519",
            "quantity": 100,
            "avg_cost": 1350.00,
            "current_price": 1384.79,
            "unrealized_pnl": 3479.0,
            "unrealized_pnl_pct": 0.0258,
            "weight": 0.25
        },
        {
            "symbol": "601318",
            "quantity": 1000,
            "avg_cost": 56.80,
            "current_price": 59.37,
            "unrealized_pnl": 2570.0,
            "unrealized_pnl_pct": 0.0453,
            "weight": 0.11
        },
        {
            "symbol": "600036",
            "quantity": 1500,
            "avg_cost": 36.50,
            "current_price": 38.27,
            "unrealized_pnl": 2655.0,
            "unrealized_pnl_pct": 0.0485,
            "weight": 0.10
        },
        {
            "symbol": "300750",
            "quantity": 200,
            "avg_cost": 420.00,
            "current_price": 436.00,
            "unrealized_pnl": 3200.0,
            "unrealized_pnl_pct": 0.0381,
            "weight": 0.16
        }
    ]

    total_value = sum(p["current_price"] * p["quantity"] for p in positions)
    total_pnl = sum(p["unrealized_pnl"] for p in positions)

    return {
        "strategy_id": strategy_id,
        "positions": positions,
        "total_positions": len(positions),
        "total_value": round(total_value, 2),
        "total_unrealized_pnl": round(total_pnl, 2),
        "cash": 45000.0,
        "portfolio_value": round(total_value + 45000, 2)
    }


@router.get("/{strategy_id}/trades")
async def get_strategy_trades(
    strategy_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """获取交易记录"""
    trades = []
    base_date = datetime.now()
    symbols = ["600519", "601318", "600036", "300750", "002594"]
    price_map = {"600519": 1385, "601318": 59, "600036": 38, "300750": 436, "002594": 103}

    for i in range(limit):
        date = base_date - timedelta(days=i // 3)
        symbol = random.choice(symbols)
        direction = random.choice(["buy", "sell"])
        base_price = price_map.get(symbol, 100)
        price = round(base_price * (1 + random.uniform(-0.03, 0.03)), 2)
        quantity = random.choice([100, 200, 300, 500, 1000])
        commission = round(price * quantity * 0.00025, 2)

        pnl = None
        if direction == "sell":
            pnl = round(random.uniform(-500, 800), 2)

        trades.append({
            "id": i + 1,
            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "value": round(price * quantity, 2),
            "commission": commission,
            "pnl": pnl,
            "signal_confidence": round(random.uniform(0.6, 0.95), 4)
        })

    return {
        "strategy_id": strategy_id,
        "trades": trades,
        "total": len(trades)
    }


@router.get("/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: int,
    period: str = Query("1Y", regex="^(1M|3M|6M|1Y|YTD|ALL)$")
):
    """获取策略表现"""
    # 生成权益曲线数据
    days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 252, "YTD": 200, "ALL": 504}
    num_days = days.get(period, 252)

    equity_curve = []
    benchmark_curve = []
    strategy_value = 1000000
    benchmark_value = 1000000

    for i in range(num_days):
        date = datetime.now() - timedelta(days=num_days - i)
        strategy_return = random.gauss(0.0005, 0.015)
        benchmark_return = random.gauss(0.0003, 0.012)

        strategy_value *= (1 + strategy_return)
        benchmark_value *= (1 + benchmark_return)

        equity_curve.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(strategy_value, 2),
            "return": round((strategy_value / 1000000 - 1) * 100, 2)
        })
        benchmark_curve.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(benchmark_value, 2),
            "return": round((benchmark_value / 1000000 - 1) * 100, 2)
        })

    total_return = (strategy_value / 1000000 - 1)
    benchmark_return = (benchmark_value / 1000000 - 1)

    return {
        "strategy_id": strategy_id,
        "period": period,
        "metrics": {
            "total_return": round(total_return, 4),
            "annual_return": round(total_return * 252 / num_days, 4),
            "sharpe_ratio": 1.42,
            "sortino_ratio": 1.85,
            "max_drawdown": -0.123,
            "win_rate": 0.58,
            "profit_factor": 1.65,
            "avg_win": 0.025,
            "avg_loss": -0.015,
            "total_trades": 156,
            "winning_trades": 90,
            "losing_trades": 66
        },
        "benchmark": {
            "total_return": round(benchmark_return, 4),
            "name": "沪深300"
        },
        "alpha": round(total_return - benchmark_return, 4),
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve
    }


@router.get("/{strategy_id}/monthly-returns")
async def get_monthly_returns(strategy_id: int):
    """获取月度收益"""
    monthly_returns = {}
    years = [2023, 2024]

    for year in years:
        monthly_returns[str(year)] = {}
        for month in range(1, 13):
            if year == 2024 and month > 12:
                break
            monthly_returns[str(year)][str(month)] = round(random.uniform(-0.08, 0.12), 4)

    return {
        "strategy_id": strategy_id,
        "monthly_returns": monthly_returns
    }


@router.post("/{strategy_id}/clone")
async def clone_strategy(strategy_id: int, new_name: str):
    """克隆策略"""
    for strategy in MOCK_STRATEGIES:
        if strategy["id"] == strategy_id:
            cloned = strategy.copy()
            cloned["id"] = len(MOCK_STRATEGIES) + 1
            cloned["name"] = new_name
            cloned["status"] = "inactive"
            cloned["created_at"] = datetime.now()
            cloned["updated_at"] = datetime.now()
            return {"message": "策略克隆成功", "strategy": cloned}

    raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 未找到")
