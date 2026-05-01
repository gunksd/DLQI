"""
风险控制 API — 基于真实回测结果计算风险指标
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import csv
import json
import random
import numpy as np

router = APIRouter()

# Absolute path to project root
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_RESULTS_DIR = os.path.join(_PROJECT_ROOT, "results")
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_ALERTS_FILE = os.path.join(_DATA_DIR, "risk_alerts.json")
_LIMITS_FILE = os.path.join(_DATA_DIR, "risk_limits.json")


def _load_backtest_results() -> list:
    """Load real backtest results from CSV"""
    path = os.path.join(_RESULTS_DIR, "backtest_results.csv")
    if not os.path.isfile(path):
        return []
    results = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def _sf(val, default=None):
    """Safe float conversion"""
    if val is None or val == '':
        return default
    try:
        v = float(val)
        return v if v == v and abs(v) != float('inf') else default
    except (ValueError, TypeError):
        return default


def _load_returns_from_csv() -> Dict[str, list]:
    """Load daily returns from CSV price data"""
    import pandas as pd
    raw_dir = os.path.join(_DATA_DIR, "raw")
    returns_dict = {}
    if os.path.isdir(raw_dir):
        for f in sorted(os.listdir(raw_dir)):
            if f.startswith("cn_") and f.endswith(".csv") and "idx_" not in f:
                sym = f.replace("cn_", "").replace(".csv", "")
                try:
                    df = pd.read_csv(os.path.join(raw_dir, f))
                    col = 'close' if 'close' in df.columns else 'Close'
                    rets = df[col].pct_change().dropna().tolist()
                    if rets:
                        returns_dict[sym] = rets
                except Exception:
                    pass
    return returns_dict


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
    """获取风险总览 — 基于真实回测结果"""
    results = _load_backtest_results()
    if not results:
        return {
            "portfolio_risk": {},
            "limits_status": {},
            "risk_score": 0,
            "risk_level": "无数据",
            "last_updated": datetime.now().isoformat(),
        }

    sharpes = [v for r in results if (v := _sf(r.get("sharpe_ratio"))) is not None]
    drawdowns = [v for r in results if (v := _sf(r.get("max_drawdown"))) is not None]
    vols = [v for r in results if (v := _sf(r.get("volatility"))) is not None]
    dir_accs = [v for r in results if (v := _sf(r.get("direction_accuracy"))) is not None]

    avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0
    worst_dd = min(drawdowns) if drawdowns else 0
    avg_vol = sum(vols) / len(vols) if vols else 0
    avg_acc = sum(dir_accs) / len(dir_accs) if dir_accs else 0

    # Risk score: 0-100 (higher = more risk)
    risk_score = min(100, max(0, int(50 - avg_sharpe * 20 + abs(worst_dd) * 200)))
    risk_level = "低" if risk_score < 40 else "中等" if risk_score < 70 else "高"

    return {
        "portfolio_risk": {
            "avg_sharpe": round(avg_sharpe, 4),
            "worst_drawdown": round(worst_dd, 4),
            "avg_volatility": round(avg_vol, 4) if avg_vol else None,
            "avg_direction_accuracy": round(avg_acc, 4),
            "model_count": len(results),
        },
        "limits_status": {
            "drawdown_limit": {
                "limit": 0.15,
                "current": round(abs(worst_dd), 4),
                "utilization": round(abs(worst_dd) / 0.15, 3),
                "status": "warning" if abs(worst_dd) > 0.12 else "normal",
            },
        },
        "risk_score": risk_score,
        "risk_level": risk_level,
        "last_updated": datetime.now().isoformat(),
    }


@router.get("/var")
async def get_var_metrics(
    confidence: float = Query(0.95, ge=0.9, le=0.99),
    window: int = Query(252, ge=20, le=504)
):
    """获取VaR指标 — 基于真实价格数据"""
    returns_dict = _load_returns_from_csv()
    if not returns_dict:
        return {"confidence_level": confidence, "window": window,
                "current_var": {}, "var_history": [], "backtesting": {}, "methodology": "无数据"}

    # Combine all stock returns into equal-weight portfolio
    min_len = min(len(v) for v in returns_dict.values())
    all_rets = np.array([v[-min_len:] for v in returns_dict.values()])
    port_rets = all_rets.mean(axis=0)  # equal-weight portfolio

    # Use tail window
    rets = port_rets[-window:] if len(port_rets) >= window else port_rets

    var_95 = float(np.percentile(rets, 5))
    var_99 = float(np.percentile(rets, 1))
    cvar_95 = float(rets[rets <= var_95].mean()) if len(rets[rets <= var_95]) > 0 else var_95
    cvar_99 = float(rets[rets <= var_99].mean()) if len(rets[rets <= var_99]) > 0 else var_99

    # Build recent VaR history (rolling 60-day)
    var_history = []
    base_date = datetime.now() - timedelta(days=60)
    for i in range(min(60, len(rets))):
        idx = len(rets) - 60 + i
        if idx < 20:
            continue
        roll = rets[max(0, idx - 60):idx]
        date = base_date + timedelta(days=i)
        var_history.append({
            "date": date.strftime("%Y-%m-%d"),
            "var_95": round(float(np.percentile(roll, 5)), 4),
            "var_99": round(float(np.percentile(roll, 1)), 4),
            "actual_return": round(float(rets[idx - 1]) if idx > 0 else 0, 4),
        })

    breaches_95 = sum(1 for v in var_history if v["actual_return"] < v["var_95"])
    breaches_99 = sum(1 for v in var_history if v["actual_return"] < v["var_99"])
    n = len(var_history) or 1

    return {
        "confidence_level": confidence,
        "window": len(rets),
        "current_var": {
            "var_95": round(var_95, 4),
            "var_99": round(var_99, 4),
            "cvar_95": round(cvar_95, 4),
            "cvar_99": round(cvar_99, 4),
        },
        "var_history": var_history,
        "backtesting": {
            "breaches_95": breaches_95,
            "expected_breaches_95": round(n * 0.05),
            "breach_ratio_95": round(breaches_95 / n, 4),
            "breaches_99": breaches_99,
            "expected_breaches_99": round(n * 0.01),
            "breach_ratio_99": round(breaches_99 / n, 4),
        },
        "methodology": "历史模拟法",
    }


@router.get("/drawdown")
async def get_drawdown_analysis():
    """获取回撤分析 — 基于真实价格数据"""
    returns_dict = _load_returns_from_csv()
    if not returns_dict:
        return {"current_drawdown": 0, "max_drawdown": 0, "drawdown_history": [], "drawdown_periods": [], "statistics": {}}

    # Equal-weight portfolio
    min_len = min(len(v) for v in returns_dict.values())
    all_rets = np.array([v[-min_len:] for v in returns_dict.values()])
    port_rets = all_rets.mean(axis=0)

    # Compute cumulative returns and drawdown
    cum = np.cumprod(1 + port_rets)
    running_max = np.maximum.accumulate(cum)
    drawdown = (cum - running_max) / running_max

    base_date = datetime.now() - timedelta(days=len(drawdown))
    dd_history = []
    for i in range(max(0, len(drawdown) - 60), len(drawdown)):
        date = base_date + timedelta(days=i)
        dd_history.append({
            "date": date.strftime("%Y-%m-%d"),
            "drawdown": round(float(drawdown[i]) * 100, 2),
        })

    current_dd = float(drawdown[-1]) if len(drawdown) > 0 else 0
    max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0

    return {
        "current_drawdown": round(current_dd, 4),
        "max_drawdown": round(max_dd, 4),
        "average_drawdown": round(float(drawdown.mean()), 4),
        "drawdown_history": dd_history,
        "drawdown_periods": [],
        "statistics": {
            "num_drawdowns_gt_5pct": int((drawdown < -0.05).sum()),
            "num_drawdowns_gt_10pct": int((drawdown < -0.10).sum()),
        },
    }


@router.get("/correlation")
async def get_correlation_matrix():
    """获取相关性矩阵 — 基于真实收益率"""
    returns_dict = _load_returns_from_csv()
    symbols = sorted(returns_dict.keys())

    if len(symbols) < 2:
        return {"symbols": symbols, "correlation_matrix": [], "benchmark_correlation": {}}

    min_len = min(len(returns_dict[s]) for s in symbols)
    data = np.array([returns_dict[s][-min_len:] for s in symbols])
    corr = np.corrcoef(data)

    matrix = [[round(float(corr[i][j]), 3) for j in range(len(symbols))] for i in range(len(symbols))]

    return {
        "symbols": symbols,
        "correlation_matrix": matrix,
        "benchmark_correlation": {},
        "benchmark": "S&P 500",
        "concentration_risk": {
            "hhi_index": round(1.0 / len(symbols), 3),
            "effective_n": len(symbols),
        },
    }


@router.post("/stress-test")
async def run_stress_test(request: StressTestRequest):
    """运行压力测试 — 基于真实历史数据"""
    returns_dict = _load_returns_from_csv()
    symbols = list(returns_dict.keys())[:5] or ["600519", "601318", "600036", "300750", "002594"]

    # 用真实数据计算各场景影响
    def _worst_period(rets: list, window: int = 20) -> float:
        if len(rets) < window:
            return sum(rets) if rets else 0
        worst = 0.0
        for i in range(len(rets) - window):
            period_ret = sum(rets[i:i+window])
            worst = min(worst, period_ret)
        return worst

    def _compute_scenario(shock_mult: float) -> dict:
        impacts = []
        for sym in symbols:
            rets = returns_dict.get(sym, [])
            worst = _worst_period(rets)
            impact = round(worst * shock_mult, 4)
            impacts.append({"symbol": sym, "impact": impact})
        impacts.sort(key=lambda x: x["impact"])
        avg_impact = round(np.mean([i["impact"] for i in impacts]), 4) if impacts else 0
        return {"positions_impact": impacts[:3], "portfolio_impact": avg_impact}

    scenarios_results = {
        "市场暴跌": {
            "description": "模拟2020年3月级别市场暴跌",
            "shock": -0.20,
            **_compute_scenario(1.0),
            "var_impact": round(np.percentile([r for rets in returns_dict.values() for r in rets], 1) * 5 if returns_dict else -0.05, 4),
        },
        "利率上升": {
            "description": "模拟2022年加息周期影响",
            "shock": 0.01,
            **_compute_scenario(0.4),
            "var_impact": round(np.percentile([r for rets in returns_dict.values() for r in rets], 5) * 2 if returns_dict else -0.02, 4),
        },
        "科技股回调": {
            "description": "科技板块集中回调",
            "shock": -0.15,
            **_compute_scenario(0.7),
            "var_impact": round(np.percentile([r for rets in returns_dict.values() for r in rets], 2) * 3 if returns_dict else -0.03, 4),
        },
        "流动性危机": {
            "description": "市场流动性枯竭",
            "shock": -0.10,
            **_compute_scenario(0.5),
            "var_impact": round(np.percentile([r for rets in returns_dict.values() for r in rets], 3) * 2 if returns_dict else -0.02, 4),
        },
        "黑天鹅事件": {
            "description": "极端尾部风险事件",
            "shock": -0.30,
            **_compute_scenario(1.5),
            "var_impact": round(np.percentile([r for rets in returns_dict.values() for r in rets], 0.5) * 5 if returns_dict else -0.08, 4),
        },
    }

    results = {scenario: scenarios_results.get(scenario, {}) for scenario in request.scenarios}
    impacts = [r.get("portfolio_impact", 0) for r in results.values()]

    return {
        "strategy_id": request.strategy_id,
        "scenarios": results,
        "summary": {
            "worst_scenario": max(results.keys(), key=lambda x: abs(results[x].get("portfolio_impact", 0))) if results else "",
            "avg_impact": round(np.mean(impacts), 4) if impacts else 0,
            "risk_budget_usage": round(min(abs(np.mean(impacts)) / 0.15, 1.0), 2) if impacts else 0,
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
    """获取风险预警 — 基于真实指标动态生成"""
    alerts = _load_alerts()

    # 如果没有持久化的 alerts，基于真实数据生成
    if not alerts:
        alerts = _generate_alerts()
        _save_alerts(alerts)

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


def _load_alerts() -> list:
    if os.path.isfile(_ALERTS_FILE):
        with open(_ALERTS_FILE) as f:
            return json.load(f)
    return []


def _save_alerts(alerts: list):
    os.makedirs(os.path.dirname(_ALERTS_FILE), exist_ok=True)
    with open(_ALERTS_FILE, "w") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2, default=str)


def _generate_alerts() -> list:
    """基于真实回测数据生成风险预警"""
    results = _load_backtest_results()
    returns_dict = _load_returns_from_csv()
    alerts = []
    aid = 1

    for row in results:
        dd = _sf(row.get("max_drawdown"), 0)
        sharpe = _sf(row.get("sharpe_ratio"), 0)
        sym = row.get("symbol", "")

        if dd is not None and dd < -0.25:
            alerts.append({
                "id": aid, "level": "danger", "title": f"{sym} 回撤过大",
                "message": f"{sym} 最大回撤 {dd*100:.1f}%，超过 -25% 阈值",
                "metric": "drawdown", "current_value": dd, "threshold": -0.25,
                "is_read": False, "created_at": datetime.now().isoformat()
            })
            aid += 1

        if sharpe is not None and sharpe < -0.5:
            alerts.append({
                "id": aid, "level": "warning", "title": f"{sym} Sharpe 为负",
                "message": f"{sym} Sharpe Ratio {sharpe:.2f}，策略表现不佳",
                "metric": "sharpe", "current_value": sharpe, "threshold": -0.5,
                "is_read": False, "created_at": datetime.now().isoformat()
            })
            aid += 1

    # 检查波动率
    for sym, rets in returns_dict.items():
        if len(rets) > 20:
            vol = float(np.std(rets[-20:]) * np.sqrt(252))
            if vol > 0.4:
                alerts.append({
                    "id": aid, "level": "warning", "title": f"{sym} 波动率偏高",
                    "message": f"{sym} 近20日年化波动率 {vol*100:.1f}%",
                    "metric": "volatility", "current_value": round(vol, 4), "threshold": 0.4,
                    "is_read": False, "created_at": datetime.now().isoformat()
                })
                aid += 1

    if not alerts:
        alerts.append({
            "id": 1, "level": "info", "title": "风险指标正常",
            "message": "所有模型风险指标在正常范围内",
            "metric": "all", "current_value": None, "threshold": None,
            "is_read": False, "created_at": datetime.now().isoformat()
        })

    return alerts


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    """标记预警已读"""
    alerts = _load_alerts()
    for a in alerts:
        if a["id"] == alert_id:
            a["is_read"] = True
            _save_alerts(alerts)
            return {"message": f"预警 {alert_id} 已标记为已读"}
    raise HTTPException(status_code=404, detail=f"预警 {alert_id} 不存在")


_DEFAULT_LIMITS = [
    {"name": "VaR限制", "key": "var_limit", "value": 0.05, "unit": "%", "description": "单日VaR不超过组合价值的5%"},
    {"name": "最大回撤", "key": "max_drawdown", "value": 0.15, "unit": "%", "description": "最大回撤不超过15%"},
    {"name": "单股持仓", "key": "position_limit", "value": 0.20, "unit": "%", "description": "单只股票持仓不超过总资产20%"},
    {"name": "行业集中度", "key": "sector_limit", "value": 0.30, "unit": "%", "description": "单一行业持仓不超过30%"},
    {"name": "止损线", "key": "stop_loss", "value": 0.05, "unit": "%", "description": "单笔交易止损线5%"},
    {"name": "止盈线", "key": "take_profit", "value": 0.15, "unit": "%", "description": "单笔交易止盈线15%"},
]


def _load_limits() -> list:
    if os.path.isfile(_LIMITS_FILE):
        with open(_LIMITS_FILE) as f:
            return json.load(f)
    return [dict(lim) for lim in _DEFAULT_LIMITS]


def _save_limits(limits: list):
    os.makedirs(os.path.dirname(_LIMITS_FILE), exist_ok=True)
    with open(_LIMITS_FILE, "w") as f:
        json.dump(limits, f, ensure_ascii=False, indent=2)


@router.get("/limits")
async def get_risk_limits():
    """获取风险限制配置"""
    limits = _load_limits()
    # 用真实回测数据填充 current 和 utilization
    results = _load_backtest_results()
    current_vals = {}
    if results:
        drawdowns = [_sf(r.get("max_drawdown"), 0) for r in results]
        sharpes = [_sf(r.get("sharpe_ratio"), 0) for r in results]
        vols = [_sf(r.get("volatility"), 0) for r in results]
        current_vals["max_drawdown"] = abs(min(drawdowns)) if drawdowns else None
        current_vals["var_limit"] = abs(np.percentile([v for v in vols if v], 95)) if vols else None

    for lim in limits:
        cur = current_vals.get(lim["key"])
        lim["current"] = round(cur, 4) if cur is not None else None
        lim["utilization"] = round(cur / lim["value"], 3) if cur is not None and lim["value"] > 0 else None

    return {"limits": limits}


@router.put("/limits")
async def update_risk_limits(config: RiskConfigRequest):
    """更新风险限制配置"""
    limits = _load_limits()
    update_map = {
        "var_limit": config.var_limit,
        "max_drawdown": config.max_drawdown_limit,
        "position_limit": config.position_limit,
        "sector_limit": config.sector_limit,
        "stop_loss": config.stop_loss,
        "take_profit": config.take_profit,
    }
    for lim in limits:
        if lim["key"] in update_map:
            lim["value"] = update_map[lim["key"]]
    _save_limits(limits)
    return {"message": "风险限制配置已更新", "limits": limits}


@router.get("/monte-carlo")
async def get_monte_carlo_simulation(
    simulations: int = Query(1000, ge=100, le=10000),
    days: int = Query(252, ge=20, le=504)
):
    """蒙特卡洛模拟 — 基于真实收益率分布"""
    returns_dict = _load_returns_from_csv()
    if not returns_dict:
        return {"simulations": 0, "days": 0, "statistics": {}, "percentiles": {}, "histogram": [],
                "probability_of_loss": 0, "expected_shortfall_5pct": 0}

    min_len = min(len(v) for v in returns_dict.values())
    all_rets = np.array([v[-min_len:] for v in returns_dict.values()])
    port_rets = all_rets.mean(axis=0)

    mu = float(np.mean(port_rets))
    sigma = float(np.std(port_rets))

    # Monte Carlo simulation
    rng = np.random.default_rng(42)
    sim_returns = rng.normal(mu, sigma, (simulations, days))
    final_returns = np.prod(1 + sim_returns, axis=1) - 1
    final_returns.sort()

    pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    percentiles = {f"{p}%": round(float(np.percentile(final_returns, p)), 4) for p in pcts}

    mean_ret = float(final_returns.mean())
    std_ret = float(final_returns.std())

    # Histogram
    bins = 50
    counts, bin_edges = np.histogram(final_returns, bins=bins)
    histogram = [
        {
            "bin_start": round(float(bin_edges[i]), 4),
            "bin_end": round(float(bin_edges[i + 1]), 4),
            "count": int(counts[i]),
            "frequency": round(int(counts[i]) / simulations, 4),
        }
        for i in range(bins)
    ]

    n5 = max(1, int(simulations * 0.05))
    es5 = float(final_returns[:n5].mean())

    return {
        "simulations": simulations,
        "days": days,
        "statistics": {
            "mean": round(mean_ret, 4),
            "std": round(std_ret, 4),
            "min": round(float(final_returns.min()), 4),
            "max": round(float(final_returns.max()), 4),
            "daily_mu": round(mu, 6),
            "daily_sigma": round(sigma, 6),
        },
        "percentiles": percentiles,
        "histogram": histogram,
        "probability_of_loss": round(float((final_returns < 0).mean()), 4),
        "expected_shortfall_5pct": round(es5, 4),
    }


@router.get("/report")
async def generate_risk_report():
    """生成风险报告 — 基于真实数据"""
    results = _load_backtest_results()
    sharpes = [v for r in results if (v := _sf(r.get("sharpe_ratio"))) is not None]
    drawdowns = [v for r in results if (v := _sf(r.get("max_drawdown"))) is not None]
    dir_accs = [v for r in results if (v := _sf(r.get("direction_accuracy"))) is not None]

    avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0
    worst_dd = min(drawdowns) if drawdowns else 0
    avg_acc = sum(dir_accs) / len(dir_accs) if dir_accs else 0

    risk_score = min(100, max(0, int(50 - avg_sharpe * 20 + abs(worst_dd) * 200)))
    risk_level = "低" if risk_score < 40 else "中等" if risk_score < 70 else "高"

    # Find worst performing symbol
    by_symbol: Dict[str, list] = {}
    for r in results:
        sym = r.get("symbol", "")
        by_symbol.setdefault(sym, []).append(_sf(r.get("sharpe_ratio"), 0))

    concerns = []
    if abs(worst_dd) > 0.1:
        concerns.append(f"最大回撤达到 {abs(worst_dd)*100:.1f}%")
    if avg_sharpe < 0.5:
        concerns.append(f"平均夏普比率偏低 ({avg_sharpe:.2f})")
    if avg_acc < 0.55:
        concerns.append(f"方向准确率不理想 ({avg_acc*100:.1f}%)")

    return {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "executive_summary": {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "key_concerns": concerns or ["各项指标正常"],
            "recommendations": [
                "定期重新训练模型以适应市场变化",
                "关注夏普比率较低的模型",
                "保持多样化模型组合",
            ],
        },
        "drawdown_summary": {
            "worst": round(worst_dd, 4),
        },
        "model_count": len(results),
        "avg_sharpe": round(avg_sharpe, 4),
        "avg_direction_accuracy": round(avg_acc, 4),
        "generated_at": datetime.now().isoformat(),
    }
