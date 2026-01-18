"""
风险控制 API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
import math

router = APIRouter()


# ==================== 请求/响应模型 ====================

class RiskConfigRequest(BaseModel):
    strategy_id: int
    var_limit: float = 0.05  # VaR限制
    max_drawdown_limit: float = 0.15  # 最大回撤限制
    position_limit: float = 0.20  # 单只股票持仓限制
    sector_limit: float = 0.30  # 单一行业限制
    stop_loss: float = 0.05  # 止损线
    take_profit: float = 0.15  # 止盈线


class StressTestRequest(BaseModel):
    strategy_id: int
    scenarios: List[str]  # 场景列表


class AlertConfig(BaseModel):
    alert_type: str
    threshold: float
    enabled: bool = True


# ==================== API端点 ====================

@router.get("/overview")
async def get_risk_overview():
    """获取风险总览"""
    return {
        "portfolio_risk": {
            "var_95": -0.0234,
            "var_99": -0.0356,
            "cvar_95": -0.0312,
            "current_drawdown": -0.045,
            "max_drawdown_30d": -0.089,
            "volatility_20d": 0.0156,
            "beta": 1.05,
            "correlation_spy": 0.78
        },
        "limits_status": {
            "var_limit": {"limit": 0.05, "current": 0.0234, "utilization": 0.468, "status": "normal"},
            "drawdown_limit": {"limit": 0.15, "current": 0.089, "utilization": 0.593, "status": "normal"},
            "position_limit": {"limit": 0.20, "current": 0.18, "utilization": 0.90, "status": "warning"},
            "sector_limit": {"limit": 0.30, "current": 0.25, "utilization": 0.833, "status": "normal"}
        },
        "risk_score": 72,  # 0-100，越高风险越大
        "risk_level": "中等",
        "last_updated": datetime.now().isoformat()
    }


@router.get("/var")
async def get_var_metrics(
    confidence: float = Query(0.95, ge=0.9, le=0.99),
    window: int = Query(252, ge=20, le=504)
):
    """获取VaR指标"""
    # 生成VaR历史数据
    var_history = []
    base_date = datetime.now() - timedelta(days=window)

    for i in range(window):
        date = base_date + timedelta(days=i)
        var_history.append({
            "date": date.strftime("%Y-%m-%d"),
            "var_95": round(-0.02 - 0.01 * random.random(), 4),
            "var_99": round(-0.03 - 0.015 * random.random(), 4),
            "cvar_95": round(-0.025 - 0.012 * random.random(), 4),
            "actual_return": round(random.gauss(0.0005, 0.015), 4)
        })

    # 计算VaR突破次数
    breaches_95 = sum(1 for v in var_history if v["actual_return"] < v["var_95"])
    breaches_99 = sum(1 for v in var_history if v["actual_return"] < v["var_99"])

    return {
        "confidence_level": confidence,
        "window": window,
        "current_var": {
            "var_95": -0.0234,
            "var_99": -0.0356,
            "cvar_95": -0.0312,
            "cvar_99": -0.0425
        },
        "var_history": var_history[-60:],  # 最近60天
        "backtesting": {
            "breaches_95": breaches_95,
            "expected_breaches_95": round(window * 0.05),
            "breach_ratio_95": round(breaches_95 / window, 4),
            "breaches_99": breaches_99,
            "expected_breaches_99": round(window * 0.01),
            "breach_ratio_99": round(breaches_99 / window, 4),
            "kupiec_test_95": "通过" if abs(breaches_95 - window * 0.05) < 5 else "未通过",
            "kupiec_test_99": "通过" if abs(breaches_99 - window * 0.01) < 3 else "未通过"
        },
        "methodology": "历史模拟法"
    }


@router.get("/drawdown")
async def get_drawdown_analysis():
    """获取回撤分析"""
    # 生成回撤历史
    drawdown_history = []
    base_date = datetime.now() - timedelta(days=252)
    current_drawdown = 0
    max_drawdown = 0

    for i in range(252):
        date = base_date + timedelta(days=i)
        # 模拟回撤变化
        change = random.gauss(0.001, 0.01)
        current_drawdown = max(min(current_drawdown + change, 0), -0.25)
        max_drawdown = min(max_drawdown, current_drawdown)

        drawdown_history.append({
            "date": date.strftime("%Y-%m-%d"),
            "drawdown": round(current_drawdown * 100, 2),
            "underwater_days": random.randint(0, 30)
        })

    # 识别主要回撤期
    drawdown_periods = [
        {
            "start_date": "2024-03-15",
            "end_date": "2024-04-20",
            "peak_date": "2024-03-15",
            "trough_date": "2024-04-05",
            "recovery_date": "2024-04-20",
            "max_drawdown": -0.123,
            "duration_days": 36,
            "recovery_days": 15
        },
        {
            "start_date": "2024-08-01",
            "end_date": "2024-09-10",
            "peak_date": "2024-08-01",
            "trough_date": "2024-08-15",
            "recovery_date": "2024-09-10",
            "max_drawdown": -0.089,
            "duration_days": 40,
            "recovery_days": 26
        }
    ]

    return {
        "current_drawdown": round(current_drawdown, 4),
        "max_drawdown": round(max_drawdown, 4),
        "average_drawdown": round(sum(d["drawdown"] for d in drawdown_history) / len(drawdown_history) / 100, 4),
        "drawdown_history": drawdown_history[-60:],
        "drawdown_periods": drawdown_periods,
        "statistics": {
            "avg_duration": 38,
            "avg_recovery": 20,
            "max_duration": 45,
            "num_drawdowns_gt_5pct": 3,
            "num_drawdowns_gt_10pct": 1
        }
    }


@router.get("/correlation")
async def get_correlation_matrix():
    """获取相关性矩阵"""
    symbols = ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA", "AMZN", "META"]
    matrix = []

    for i, sym1 in enumerate(symbols):
        row = []
        for j, sym2 in enumerate(symbols):
            if i == j:
                row.append(1.0)
            elif i < j:
                corr = round(0.3 + 0.5 * random.random(), 3)
                row.append(corr)
            else:
                row.append(matrix[j][i])
        matrix.append(row)

    # 与基准的相关性
    benchmark_correlation = {sym: round(0.5 + 0.4 * random.random(), 3) for sym in symbols}

    return {
        "symbols": symbols,
        "correlation_matrix": matrix,
        "benchmark_correlation": benchmark_correlation,
        "benchmark": "沪深300",
        "eigenvalues": [round(random.uniform(0.5, 3.0), 3) for _ in range(len(symbols))],
        "concentration_risk": {
            "hhi_index": 0.18,  # Herfindahl-Hirschman Index
            "effective_n": 5.5,  # 有效持仓数量
            "top3_concentration": 0.45
        }
    }


@router.post("/stress-test")
async def run_stress_test(request: StressTestRequest):
    """运行压力测试"""
    scenarios_results = {
        "市场暴跌": {
            "description": "市场整体下跌20%",
            "shock": -0.20,
            "portfolio_impact": round(-0.20 * (0.8 + 0.4 * random.random()), 4),
            "var_impact": round(-0.035 * (1 + 0.3 * random.random()), 4),
            "positions_impact": [
                {"symbol": "NVDA", "impact": -0.28},
                {"symbol": "TSLA", "impact": -0.25},
                {"symbol": "AAPL", "impact": -0.18}
            ]
        },
        "利率上升": {
            "description": "利率上升100bp",
            "shock": 0.01,
            "portfolio_impact": round(-0.05 * (0.8 + 0.4 * random.random()), 4),
            "var_impact": round(-0.008 * (1 + 0.3 * random.random()), 4),
            "positions_impact": [
                {"symbol": "MSFT", "impact": -0.08},
                {"symbol": "GOOGL", "impact": -0.06},
                {"symbol": "AMZN", "impact": -0.07}
            ]
        },
        "科技股回调": {
            "description": "科技板块下跌15%",
            "shock": -0.15,
            "portfolio_impact": round(-0.15 * (0.6 + 0.3 * random.random()), 4),
            "var_impact": round(-0.025 * (1 + 0.3 * random.random()), 4),
            "positions_impact": [
                {"symbol": "NVDA", "impact": -0.20},
                {"symbol": "META", "impact": -0.16},
                {"symbol": "AAPL", "impact": -0.12}
            ]
        },
        "流动性危机": {
            "description": "市场流动性枯竭",
            "shock": -0.10,
            "portfolio_impact": round(-0.12 * (0.8 + 0.4 * random.random()), 4),
            "var_impact": round(-0.02 * (1 + 0.3 * random.random()), 4),
            "positions_impact": [
                {"symbol": "TSLA", "impact": -0.18},
                {"symbol": "NVDA", "impact": -0.15},
                {"symbol": "META", "impact": -0.12}
            ]
        },
        "黑天鹅事件": {
            "description": "极端尾部风险事件",
            "shock": -0.30,
            "portfolio_impact": round(-0.30 * (0.7 + 0.4 * random.random()), 4),
            "var_impact": round(-0.05 * (1 + 0.3 * random.random()), 4),
            "positions_impact": [
                {"symbol": "TSLA", "impact": -0.40},
                {"symbol": "NVDA", "impact": -0.35},
                {"symbol": "META", "impact": -0.32}
            ]
        }
    }

    results = {scenario: scenarios_results.get(scenario, {}) for scenario in request.scenarios}

    return {
        "strategy_id": request.strategy_id,
        "scenarios": results,
        "summary": {
            "worst_scenario": max(results.keys(), key=lambda x: abs(results[x].get("portfolio_impact", 0))),
            "avg_impact": round(sum(r.get("portfolio_impact", 0) for r in results.values()) / len(results), 4),
            "risk_budget_usage": round(random.uniform(0.6, 0.9), 2)
        },
        "recommendations": [
            "考虑增加对冲头寸以降低尾部风险",
            "科技股集中度较高，建议适当分散",
            "可考虑增加防御性资产配置"
        ]
    }


@router.get("/alerts")
async def get_risk_alerts(
    level: Optional[str] = None,
    is_read: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """获取风险预警"""
    alerts = [
        {
            "id": 1,
            "level": "danger",
            "title": "单股持仓超限",
            "message": "NVDA持仓占比达到18.5%，接近20%限制",
            "strategy_id": 1,
            "metric": "position_limit",
            "current_value": 0.185,
            "threshold": 0.20,
            "is_read": False,
            "created_at": datetime.now() - timedelta(hours=2)
        },
        {
            "id": 2,
            "level": "warning",
            "title": "回撤接近阈值",
            "message": "当前回撤-8.9%，接近-10%预警线",
            "strategy_id": 1,
            "metric": "drawdown",
            "current_value": -0.089,
            "threshold": -0.10,
            "is_read": False,
            "created_at": datetime.now() - timedelta(hours=5)
        },
        {
            "id": 3,
            "level": "info",
            "title": "波动率上升",
            "message": "20日波动率从1.2%升至1.56%",
            "strategy_id": 1,
            "metric": "volatility",
            "current_value": 0.0156,
            "threshold": 0.02,
            "is_read": True,
            "created_at": datetime.now() - timedelta(days=1)
        },
        {
            "id": 4,
            "level": "warning",
            "title": "相关性过高",
            "message": "AAPL与MSFT相关性达0.85，超过0.8阈值",
            "strategy_id": 1,
            "metric": "correlation",
            "current_value": 0.85,
            "threshold": 0.80,
            "is_read": True,
            "created_at": datetime.now() - timedelta(days=2)
        },
        {
            "id": 5,
            "level": "danger",
            "title": "VaR突破",
            "message": "实际损失-2.8%超过VaR(95%)预测-2.34%",
            "strategy_id": 1,
            "metric": "var_breach",
            "current_value": -0.028,
            "threshold": -0.0234,
            "is_read": False,
            "created_at": datetime.now() - timedelta(days=3)
        }
    ]

    if level:
        alerts = [a for a in alerts if a["level"] == level]
    if is_read is not None:
        alerts = [a for a in alerts if a["is_read"] == is_read]

    return {
        "alerts": alerts[:limit],
        "total": len(alerts),
        "unread_count": sum(1 for a in alerts if not a["is_read"]),
        "by_level": {
            "danger": sum(1 for a in alerts if a["level"] == "danger"),
            "warning": sum(1 for a in alerts if a["level"] == "warning"),
            "info": sum(1 for a in alerts if a["level"] == "info")
        }
    }


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    """标记预警已读"""
    return {"message": f"预警 {alert_id} 已标记为已读"}


@router.get("/limits")
async def get_risk_limits():
    """获取风险限制配置"""
    return {
        "limits": [
            {
                "name": "VaR限制",
                "key": "var_limit",
                "value": 0.05,
                "current": 0.0234,
                "utilization": 0.468,
                "unit": "%",
                "description": "单日VaR不超过组合价值的5%"
            },
            {
                "name": "最大回撤",
                "key": "max_drawdown",
                "value": 0.15,
                "current": 0.089,
                "utilization": 0.593,
                "unit": "%",
                "description": "最大回撤不超过15%"
            },
            {
                "name": "单股持仓",
                "key": "position_limit",
                "value": 0.20,
                "current": 0.185,
                "utilization": 0.925,
                "unit": "%",
                "description": "单只股票持仓不超过总资产20%"
            },
            {
                "name": "行业集中度",
                "key": "sector_limit",
                "value": 0.30,
                "current": 0.25,
                "utilization": 0.833,
                "unit": "%",
                "description": "单一行业持仓不超过30%"
            },
            {
                "name": "止损线",
                "key": "stop_loss",
                "value": 0.05,
                "current": None,
                "utilization": None,
                "unit": "%",
                "description": "单笔交易止损线5%"
            },
            {
                "name": "止盈线",
                "key": "take_profit",
                "value": 0.15,
                "current": None,
                "utilization": None,
                "unit": "%",
                "description": "单笔交易止盈线15%"
            }
        ]
    }


@router.put("/limits")
async def update_risk_limits(config: RiskConfigRequest):
    """更新风险限制配置"""
    return {
        "message": "风险限制配置已更新",
        "config": {
            "var_limit": config.var_limit,
            "max_drawdown_limit": config.max_drawdown_limit,
            "position_limit": config.position_limit,
            "sector_limit": config.sector_limit,
            "stop_loss": config.stop_loss,
            "take_profit": config.take_profit
        }
    }


@router.get("/monte-carlo")
async def get_monte_carlo_simulation(
    simulations: int = Query(1000, ge=100, le=10000),
    days: int = Query(252, ge=20, le=504)
):
    """蒙特卡洛模拟"""
    # 生成模拟结果分布
    final_returns = []
    for _ in range(simulations):
        cumulative_return = 1.0
        for _ in range(days):
            daily_return = random.gauss(0.0005, 0.015)
            cumulative_return *= (1 + daily_return)
        final_returns.append(cumulative_return - 1)

    final_returns.sort()

    # 计算分位数
    percentiles = {
        "1%": round(final_returns[int(simulations * 0.01)], 4),
        "5%": round(final_returns[int(simulations * 0.05)], 4),
        "10%": round(final_returns[int(simulations * 0.10)], 4),
        "25%": round(final_returns[int(simulations * 0.25)], 4),
        "50%": round(final_returns[int(simulations * 0.50)], 4),
        "75%": round(final_returns[int(simulations * 0.75)], 4),
        "90%": round(final_returns[int(simulations * 0.90)], 4),
        "95%": round(final_returns[int(simulations * 0.95)], 4),
        "99%": round(final_returns[int(simulations * 0.99)], 4)
    }

    # 生成直方图数据
    bins = 50
    min_val, max_val = min(final_returns), max(final_returns)
    bin_width = (max_val - min_val) / bins
    histogram = []
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(1 for r in final_returns if bin_start <= r < bin_end)
        histogram.append({
            "bin_start": round(bin_start, 4),
            "bin_end": round(bin_end, 4),
            "count": count,
            "frequency": round(count / simulations, 4)
        })

    return {
        "simulations": simulations,
        "days": days,
        "statistics": {
            "mean": round(sum(final_returns) / len(final_returns), 4),
            "std": round(math.sqrt(sum((r - sum(final_returns)/len(final_returns))**2 for r in final_returns) / len(final_returns)), 4),
            "min": round(min(final_returns), 4),
            "max": round(max(final_returns), 4),
            "skewness": round(random.uniform(-0.5, 0.5), 4),
            "kurtosis": round(random.uniform(2.5, 4.0), 4)
        },
        "percentiles": percentiles,
        "histogram": histogram,
        "probability_of_loss": round(sum(1 for r in final_returns if r < 0) / simulations, 4),
        "expected_shortfall_5pct": round(sum(final_returns[:int(simulations * 0.05)]) / int(simulations * 0.05), 4)
    }


@router.get("/report")
async def generate_risk_report():
    """生成风险报告"""
    return {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "executive_summary": {
            "risk_level": "中等",
            "risk_score": 72,
            "key_concerns": [
                "单股持仓接近上限",
                "科技板块集中度较高",
                "近期波动率上升"
            ],
            "recommendations": [
                "减持NVDA至15%以下",
                "增加非科技板块配置",
                "考虑增加对冲头寸"
            ]
        },
        "var_summary": {
            "var_95": -0.0234,
            "var_99": -0.0356,
            "var_limit_utilization": 0.468
        },
        "drawdown_summary": {
            "current": -0.045,
            "max_30d": -0.089,
            "limit_utilization": 0.593
        },
        "concentration_summary": {
            "top_position": {"symbol": "NVDA", "weight": 0.185},
            "top_sector": {"sector": "科技", "weight": 0.45},
            "hhi_index": 0.18
        },
        "generated_at": datetime.now().isoformat()
    }
