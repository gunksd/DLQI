"""
回测系统 API — 使用真实回测结果
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import csv

router = APIRouter()


# ==================== 请求模型 ====================

class BacktestRequest(BaseModel):
    model_id: str
    symbol: str
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003
    slippage: float = 0.001


# ==================== 回测结果读取 ====================

def _find_results_csv() -> Optional[str]:
    """找到 backtest_results.csv"""
    candidates = [
        "./results/backtest_results.csv",
        "/app/results/backtest_results.csv",
        "/data/results/backtest_results.csv",
        os.path.join(os.getenv("DATA_DIR", "./data"), "..", "results", "backtest_results.csv"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_all_results() -> List[dict]:
    """加载所有回测结果"""
    path = _find_results_csv()
    if not path:
        return []
    results = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def _safe_float(val, default=None):
    if val is None or val == '':
        return default
    try:
        v = float(val)
        if v != v or v == float('inf') or v == float('-inf'):
            return default
        return round(v, 6)
    except (ValueError, TypeError):
        return default


def _format_result(row: dict, idx: int) -> dict:
    """格式化单条回测结果"""
    return {
        "id": idx,
        "model_id": row.get("model_id", ""),
        "model_type": row.get("model_type", ""),
        "symbol": row.get("symbol", ""),
        "total_return": _safe_float(row.get("total_return")),
        "annual_return": _safe_float(row.get("annual_return")),
        "volatility": _safe_float(row.get("volatility")),
        "max_drawdown": _safe_float(row.get("max_drawdown")),
        "sharpe_ratio": _safe_float(row.get("sharpe_ratio")),
        "sortino_ratio": _safe_float(row.get("sortino_ratio")),
        "calmar_ratio": _safe_float(row.get("calmar_ratio")),
        "direction_accuracy": _safe_float(row.get("direction_accuracy")),
        "win_rate": _safe_float(row.get("win_rate")),
        "profit_factor": _safe_float(row.get("profit_factor")),
        "n_trades": int(float(row.get("n_trades", 0))),
        "total_commission": _safe_float(row.get("total_commission")),
        "benchmark_return": _safe_float(row.get("benchmark_return")),
        "excess_return": _safe_float(row.get("excess_return")),
        "status": "completed",
    }


# ==================== API 端点 ====================

@router.get("/")
async def get_backtest_results(
    symbol: Optional[str] = None,
    model_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """获取所有回测结果"""
    all_results = _load_all_results()
    formatted = [_format_result(r, i + 1) for i, r in enumerate(all_results)]

    if symbol:
        formatted = [r for r in formatted if r["symbol"] == symbol]
    if model_type:
        formatted = [r for r in formatted if r["model_type"] == model_type]

    total = len(formatted)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": formatted[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
async def get_backtest_summary():
    """回测结果总览 — 按模型类型和股票分组"""
    all_results = _load_all_results()
    if not all_results:
        return {"summary": {}, "best_models": []}

    # 按 model_type 分组统计
    by_type: Dict[str, list] = {}
    for row in all_results:
        mt = row.get("model_type", "unknown")
        by_type.setdefault(mt, []).append(row)

    summary = {}
    for mt, rows in by_type.items():
        sharpes = [v for r in rows if (v := _safe_float(r.get("sharpe_ratio"))) is not None]
        returns = [v for r in rows if (v := _safe_float(r.get("total_return"))) is not None]
        accuracies = [v for r in rows if (v := _safe_float(r.get("direction_accuracy"))) is not None]
        summary[mt] = {
            "count": len(rows),
            "avg_sharpe": round(sum(sharpes) / len(sharpes), 4) if sharpes else None,
            "avg_return": round(sum(returns) / len(returns), 4) if returns else None,
            "avg_direction_accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else None,
        }

    # 最优模型（按 Sharpe 排序）
    best = sorted(all_results, key=lambda r: _safe_float(r.get("sharpe_ratio"), 0), reverse=True)
    best_models = [_format_result(r, i + 1) for i, r in enumerate(best[:5])]

    return {"summary": summary, "best_models": best_models}


@router.get("/compare")
async def compare_by_symbol(symbol: str):
    """对比同一股票的不同模型回测结果"""
    all_results = _load_all_results()
    filtered = [r for r in all_results if r.get("symbol") == symbol]
    if not filtered:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的回测结果")

    comparison = [_format_result(r, i + 1) for i, r in enumerate(filtered)]
    # 按 Sharpe 排序
    comparison.sort(key=lambda x: x.get("sharpe_ratio") or 0, reverse=True)
    return {"symbol": symbol, "models": comparison}


@router.get("/heatmap")
async def get_sharpe_heatmap():
    """获取 Sharpe 热力图数据（model_type x symbol）"""
    all_results = _load_all_results()
    if not all_results:
        return {"symbols": [], "model_types": [], "data": []}

    symbols = sorted(set(r.get("symbol", "") for r in all_results))
    model_types = sorted(set(r.get("model_type", "") for r in all_results))

    data = []
    for row in all_results:
        data.append({
            "model_type": row.get("model_type", ""),
            "symbol": row.get("symbol", ""),
            "sharpe_ratio": _safe_float(row.get("sharpe_ratio"), 0),
            "total_return": _safe_float(row.get("total_return"), 0),
            "direction_accuracy": _safe_float(row.get("direction_accuracy"), 0),
        })

    return {"symbols": symbols, "model_types": model_types, "data": data}


@router.get("/{model_id}")
async def get_backtest_by_model(model_id: str):
    """获取指定模型的回测结果"""
    all_results = _load_all_results()
    for i, row in enumerate(all_results):
        if row.get("model_id") == model_id:
            return _format_result(row, i + 1)
    raise HTTPException(status_code=404, detail=f"未找到模型 {model_id} 的回测结果")
