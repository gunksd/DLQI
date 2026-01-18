"""
回测系统 API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
import math

router = APIRouter()


# ==================== 请求/响应模型 ====================

class BacktestRequest(BaseModel):
    strategy_id: int
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003
    slippage: float = 0.001
    benchmark: str = "000300.SH"  # 沪深300


class OptimizationRequest(BaseModel):
    strategy_id: int
    symbols: List[str]
    start_date: str
    end_date: str
    param_ranges: Dict[str, Dict[str, float]]
    optimization_target: str = "sharpe_ratio"
    n_trials: int = 100


# ==================== 模拟数据生成 ====================

def generate_equity_curve(days: int, initial_capital: float, annual_return: float = 0.185):
    """生成权益曲线"""
    daily_return = (1 + annual_return) ** (1/252) - 1
    volatility = 0.015

    equity = [initial_capital]
    dates = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_date + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))

        ret = random.gauss(daily_return, volatility)
        equity.append(equity[-1] * (1 + ret))

    return dates, equity[1:]


def generate_drawdown_curve(equity: List[float]):
    """生成回撤曲线"""
    peak = equity[0]
    drawdowns = []

    for value in equity:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak
        drawdowns.append(round(drawdown * 100, 2))

    return drawdowns


def generate_trades(days: int, symbols: List[str]):
    """生成交易记录"""
    trades = []
    base_date = datetime.now() - timedelta(days=days)

    trade_id = 1
    for i in range(0, days, random.randint(2, 5)):
        date = base_date + timedelta(days=i)
        symbol = random.choice(symbols)
        direction = random.choice(["buy", "sell"])
        quantity = random.randint(100, 1000)
        price = round(random.uniform(50, 500), 2)
        commission = round(price * quantity * 0.0003, 2)
        slippage = round(price * quantity * 0.001, 2)

        pnl = None
        pnl_pct = None
        if direction == "sell":
            pnl = round(random.uniform(-2000, 5000), 2)
            pnl_pct = round(pnl / (price * quantity), 4)

        trades.append({
            "id": trade_id,
            "date": date.strftime("%Y-%m-%d"),
            "time": f"{random.randint(9, 15):02d}:{random.randint(0, 59):02d}:00",
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "value": round(price * quantity, 2),
            "commission": commission,
            "slippage": slippage,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        })
        trade_id += 1

    return trades


# ==================== API端点 ====================

@router.get("/")
async def get_backtest_history(
    strategy_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取回测历史"""
    results = [
        {
            "id": 1,
            "strategy_id": 1,
            "strategy_name": "ML集成策略",
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 1000000,
            "final_capital": 1185000,
            "total_return": 0.185,
            "sharpe_ratio": 1.42,
            "max_drawdown": -0.123,
            "status": "completed",
            "created_at": datetime.now() - timedelta(days=1)
        },
        {
            "id": 2,
            "strategy_id": 2,
            "strategy_name": "动量反转策略",
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 1000000,
            "final_capital": 1142000,
            "total_return": 0.142,
            "sharpe_ratio": 1.15,
            "max_drawdown": -0.156,
            "status": "completed",
            "created_at": datetime.now() - timedelta(days=3)
        },
        {
            "id": 3,
            "strategy_id": 3,
            "strategy_name": "混合策略Alpha",
            "start_date": "2023-06-01",
            "end_date": "2024-12-31",
            "initial_capital": 1000000,
            "final_capital": 1168000,
            "total_return": 0.168,
            "sharpe_ratio": 1.35,
            "max_drawdown": -0.135,
            "status": "completed",
            "created_at": datetime.now() - timedelta(days=7)
        }
    ]

    if strategy_id:
        results = [r for r in results if r["strategy_id"] == strategy_id]

    return {
        "items": results,
        "total": len(results),
        "page": page,
        "page_size": page_size
    }


@router.post("/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """运行回测"""
    backtest_id = random.randint(1000, 9999)

    return {
        "message": "回测任务已启动",
        "backtest_id": backtest_id,
        "status": "running",
        "config": {
            "strategy_id": request.strategy_id,
            "symbols": request.symbols,
            "date_range": f"{request.start_date} ~ {request.end_date}",
            "initial_capital": request.initial_capital,
            "commission_rate": request.commission_rate,
            "slippage": request.slippage,
            "benchmark": request.benchmark
        }
    }


@router.get("/{backtest_id}")
async def get_backtest_result(backtest_id: int):
    """获取回测结果详情"""
    days = 504  # 2年
    initial_capital = 1000000.0

    dates, equity = generate_equity_curve(days, initial_capital)
    drawdowns = generate_drawdown_curve(equity)

    # 生成基准曲线
    _, benchmark_equity = generate_equity_curve(days, initial_capital, annual_return=0.072)

    final_capital = equity[-1]
    total_return = (final_capital - initial_capital) / initial_capital
    max_dd = min(drawdowns) / 100

    # 计算其他指标
    daily_returns = [(equity[i] - equity[i-1]) / equity[i-1] for i in range(1, len(equity))]
    avg_return = sum(daily_returns) / len(daily_returns)
    std_return = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
    sharpe = (avg_return * 252) / (std_return * math.sqrt(252)) if std_return > 0 else 0

    trades = generate_trades(days, ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"])
    winning_trades = [t for t in trades if t["pnl"] and t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] and t["pnl"] < 0]

    return {
        "id": backtest_id,
        "strategy_id": 1,
        "strategy_name": "ML集成策略",
        "config": {
            "start_date": dates[0],
            "end_date": dates[-1],
            "initial_capital": initial_capital,
            "commission_rate": 0.0003,
            "slippage": 0.001,
            "benchmark": "沪深300"
        },
        "summary": {
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return, 4),
            "annual_return": round(total_return * 252 / days, 4),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sharpe * 1.3, 2),
            "max_drawdown": round(max_dd, 4),
            "calmar_ratio": round(abs(total_return / max_dd) if max_dd != 0 else 0, 2),
            "win_rate": round(len(winning_trades) / (len(winning_trades) + len(losing_trades)), 4) if trades else 0,
            "profit_factor": round(sum(t["pnl"] for t in winning_trades) / abs(sum(t["pnl"] for t in losing_trades)), 2) if losing_trades else 0,
            "total_trades": len([t for t in trades if t["direction"] == "sell"]),
            "avg_trade_return": round(sum(t["pnl"] or 0 for t in trades) / len(trades), 2) if trades else 0,
            "max_consecutive_wins": random.randint(5, 12),
            "max_consecutive_losses": random.randint(3, 7)
        },
        "benchmark_comparison": {
            "strategy_return": round(total_return, 4),
            "benchmark_return": round((benchmark_equity[-1] - initial_capital) / initial_capital, 4),
            "alpha": round(total_return - (benchmark_equity[-1] - initial_capital) / initial_capital, 4),
            "beta": round(random.uniform(0.8, 1.2), 2),
            "information_ratio": round(random.uniform(0.5, 1.5), 2)
        },
        "equity_curve": [
            {"date": dates[i], "strategy": round(equity[i], 2), "benchmark": round(benchmark_equity[i], 2)}
            for i in range(len(dates))
        ],
        "drawdown_curve": [
            {"date": dates[i], "drawdown": drawdowns[i]}
            for i in range(len(dates))
        ],
        "monthly_returns": _generate_monthly_returns(),
        "status": "completed",
        "created_at": datetime.now().isoformat()
    }


def _generate_monthly_returns():
    """生成月度收益表格"""
    returns = {}
    for year in [2023, 2024]:
        returns[str(year)] = {}
        for month in range(1, 13):
            if year == 2024 and month > 12:
                break
            returns[str(year)][str(month)] = round(random.uniform(-0.08, 0.12), 4)
    return returns


@router.get("/{backtest_id}/trades")
async def get_backtest_trades(
    backtest_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """获取回测交易记录"""
    trades = generate_trades(504, ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"])

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "backtest_id": backtest_id,
        "trades": trades[start:end],
        "total": len(trades),
        "page": page,
        "page_size": page_size
    }


@router.get("/{backtest_id}/positions")
async def get_backtest_positions(backtest_id: int):
    """获取回测持仓变化"""
    days = 504
    base_date = datetime.now() - timedelta(days=days)
    positions_history = []

    for i in range(0, days, 5):  # 每5天记录一次
        date = base_date + timedelta(days=i)
        num_positions = random.randint(3, 8)

        positions = []
        symbols = random.sample(["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "NFLX"], num_positions)

        for symbol in symbols:
            positions.append({
                "symbol": symbol,
                "weight": round(random.uniform(0.05, 0.25), 4),
                "value": round(random.uniform(50000, 200000), 2)
            })

        # 归一化权重
        total_weight = sum(p["weight"] for p in positions)
        for p in positions:
            p["weight"] = round(p["weight"] / total_weight, 4)

        positions_history.append({
            "date": date.strftime("%Y-%m-%d"),
            "positions": positions,
            "cash_weight": round(random.uniform(0.05, 0.2), 4)
        })

    return {
        "backtest_id": backtest_id,
        "positions_history": positions_history
    }


@router.get("/{backtest_id}/analysis")
async def get_backtest_analysis(backtest_id: int):
    """获取回测分析报告"""
    return {
        "backtest_id": backtest_id,
        "risk_analysis": {
            "var_95": -0.0234,
            "var_99": -0.0356,
            "cvar_95": -0.0312,
            "volatility_annual": 0.156,
            "downside_deviation": 0.098,
            "tail_ratio": 1.25
        },
        "return_analysis": {
            "best_day": {"date": "2024-03-15", "return": 0.0456},
            "worst_day": {"date": "2024-08-05", "return": -0.0389},
            "best_month": {"month": "2024-02", "return": 0.0823},
            "worst_month": {"month": "2024-09", "return": -0.0567},
            "positive_months": 15,
            "negative_months": 9,
            "average_monthly_return": 0.0156
        },
        "trade_analysis": {
            "avg_holding_period": 5.2,
            "avg_profit_per_trade": 1250.0,
            "avg_loss_per_trade": -780.0,
            "largest_win": 8500.0,
            "largest_loss": -4200.0,
            "trades_per_month": 13.5
        },
        "sector_analysis": [
            {"sector": "科技", "weight": 0.45, "return": 0.22},
            {"sector": "消费", "weight": 0.20, "return": 0.15},
            {"sector": "医疗", "weight": 0.15, "return": 0.12},
            {"sector": "金融", "weight": 0.12, "return": 0.08},
            {"sector": "工业", "weight": 0.08, "return": 0.10}
        ],
        "attribution": {
            "stock_selection": 0.085,
            "market_timing": 0.045,
            "sector_allocation": 0.025,
            "residual": 0.030
        }
    }


@router.post("/optimize")
async def run_optimization(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """运行参数优化"""
    optimization_id = random.randint(1000, 9999)

    return {
        "message": "参数优化任务已启动",
        "optimization_id": optimization_id,
        "status": "running",
        "config": {
            "strategy_id": request.strategy_id,
            "symbols": request.symbols,
            "date_range": f"{request.start_date} ~ {request.end_date}",
            "param_ranges": request.param_ranges,
            "target": request.optimization_target,
            "n_trials": request.n_trials
        }
    }


@router.get("/optimization/{optimization_id}")
async def get_optimization_result(optimization_id: int):
    """获取优化结果"""
    trials = []
    for i in range(100):
        trials.append({
            "trial_id": i + 1,
            "params": {
                "threshold": round(0.5 + 0.3 * random.random(), 2),
                "holding_period": random.randint(3, 10),
                "position_size": round(0.05 + 0.15 * random.random(), 2)
            },
            "metrics": {
                "total_return": round(0.1 + 0.15 * random.random(), 4),
                "sharpe_ratio": round(0.8 + 0.8 * random.random(), 2),
                "max_drawdown": round(-0.2 + 0.1 * random.random(), 4)
            },
            "value": round(0.8 + 0.8 * random.random(), 2)  # 优化目标值
        })

    best_trial = max(trials, key=lambda x: x["value"])

    return {
        "optimization_id": optimization_id,
        "status": "completed",
        "trials": trials,
        "best_trial": best_trial,
        "best_params": best_trial["params"],
        "best_metrics": best_trial["metrics"],
        "optimization_history": [
            {"trial": i + 1, "best_value": max(t["value"] for t in trials[:i+1])}
            for i in range(len(trials))
        ]
    }


@router.post("/compare")
async def compare_backtests(backtest_ids: List[int]):
    """对比多个回测结果"""
    comparison = []

    for bid in backtest_ids:
        comparison.append({
            "backtest_id": bid,
            "strategy_name": f"策略{bid % 4 + 1}",
            "total_return": round(0.1 + 0.1 * random.random(), 4),
            "annual_return": round(0.08 + 0.08 * random.random(), 4),
            "sharpe_ratio": round(0.8 + 0.8 * random.random(), 2),
            "max_drawdown": round(-0.2 + 0.1 * random.random(), 4),
            "win_rate": round(0.45 + 0.15 * random.random(), 4),
            "profit_factor": round(1.2 + 0.6 * random.random(), 2)
        })

    return {"comparison": comparison}


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: int):
    """删除回测记录"""
    return {"message": f"回测记录 {backtest_id} 已删除"}
