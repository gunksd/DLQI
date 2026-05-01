"""
回测系统 API — 使用真实回测结果
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import csv
import json
import subprocess

from app.services.job_service import job_service

router = APIRouter()

# Compute absolute project root from this file's location
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_RESULTS_DIR = os.path.join(_PROJECT_ROOT, "results")
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


# ==================== Pipeline 执行函数 ====================

def _run_pipeline_task(params: dict, progress_cb):
    """Pipeline 任务函数（在线程池中执行）"""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    venv_python = os.path.join(root_dir, "backend", "venv", "bin", "python")
    script = os.path.join(root_dir, "scripts", "run_pipeline.py")

    if not os.path.isfile(venv_python):
        venv_python = "python3"
    if not os.path.isfile(script):
        raise FileNotFoundError(f"Pipeline 脚本不存在: {script}")

    progress_cb(10, "正在运行 pipeline...")

    result = subprocess.run(
        [venv_python, script],
        cwd=root_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:] if result.stderr else "未知错误")

    progress_cb(100, "Pipeline 完成")
    return {"message": "Pipeline 运行成功"}


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
    p = os.path.join(_RESULTS_DIR, "backtest_results.csv")
    return p if os.path.isfile(p) else None


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

@router.post("/run")
async def run_pipeline():
    """触发 pipeline 运行（训练 → 预测 → 回测 → 分析）"""
    job_id = await job_service.submit(
        job_type="pipeline",
        func=_run_pipeline_task,
        params={},
    )
    return {"message": "Pipeline 已启动", "job_id": job_id, "status": "running"}


@router.get("/status")
async def get_pipeline_status():
    """获取 pipeline 运行状态（兼容前端轮询）"""
    jobs = await job_service.list_jobs(limit=5)
    pipeline_jobs = [j for j in jobs if j["job_type"] == "pipeline"]
    if not pipeline_jobs:
        return {"running": False, "progress": "", "error": None, "last_run": None}
    latest = pipeline_jobs[0]
    return {
        "running": latest["status"] in ("pending", "running"),
        "progress": latest["current_step"],
        "error": None if latest["status"] != "failed" else "Pipeline 运行失败",
        "last_run": latest["created_at"],
        "job_id": latest["id"],
    }


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


@router.get("/recommend")
async def get_recommended_strategy(symbol: Optional[str] = None):
    """
    策略综合评分与推荐
    - 指定 symbol 时：推荐该股票上表现最好的模型
    - 不指定时：推荐全局最优
    评分权重：Sharpe 40% + 年化收益 30% + 最大回撤 20% + 方向准确率 10%
    """
    all_results = _load_all_results()
    if not all_results:
        return {"top": [], "best": None, "scoring_weights": {}}

    # 过滤掉无效行（n_trades=0 且 sharpe=0 的无意义结果）
    valid = [r for r in all_results if int(float(r.get("n_trades", 0))) > 0]
    if not valid:
        valid = all_results

    # 按股票筛选
    if symbol:
        valid = [r for r in valid if r.get("symbol", "") == symbol]
        if not valid:
            return {"top": [], "best": None, "symbol": symbol, "message": f"没有 {symbol} 的回测结果"}

    def _score(row: dict) -> float:
        sharpe = _safe_float(row.get("sharpe_ratio"), 0) or 0
        annual = _safe_float(row.get("annual_return"), 0) or 0
        drawdown = _safe_float(row.get("max_drawdown"), 0) or 0  # 负值
        accuracy = _safe_float(row.get("direction_accuracy"), 0) or 0

        # 归一化到 [0,1]：drawdown 越小（越接近0）越好
        sharpe_norm = min(max(sharpe / 4.0, 0), 1)
        annual_norm = min(max(annual / 1.0, 0), 1)
        drawdown_norm = min(max(1 + drawdown, 0), 1)  # drawdown 是负数
        accuracy_norm = min(max(accuracy, 0), 1)

        # MULTI 模型稳定性加分：跨股票泛化能力
        stability_bonus = 0.05 if "MULTI" in row.get("model_id", "") else 0

        return round(
            sharpe_norm * 0.35
            + annual_norm * 0.25
            + drawdown_norm * 0.20
            + accuracy_norm * 0.10
            + stability_bonus
            + 0.10,  # 基础分
            4,
        )

    scored = []
    for i, row in enumerate(valid):
        result = _format_result(row, i + 1)
        score = _score(row)
        sharpe = result.get("sharpe_ratio") or 0
        annual = result.get("annual_return") or 0
        drawdown = result.get("max_drawdown") or 0
        accuracy = result.get("direction_accuracy") or 0
        result["composite_score"] = score
        result["score_breakdown"] = {
            "sharpe_score": round(min(max(sharpe / 4.0, 0), 1) * 0.35, 4),
            "return_score": round(min(max(annual / 1.0, 0), 1) * 0.25, 4),
            "drawdown_score": round(min(max(1 + drawdown, 0), 1) * 0.20, 4),
            "accuracy_score": round(min(max(accuracy, 0), 1) * 0.10, 4),
            "stability_bonus": 0.05 if "MULTI" in (result.get("model_id") or "") else 0,
        }
        scored.append(result)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    top3 = scored[:3]

    return {
        "top": top3,
        "best": top3[0] if top3 else None,
        "symbol": symbol,
        "scoring_weights": {
            "sharpe_ratio": 0.35,
            "annual_return": 0.25,
            "max_drawdown": 0.20,
            "direction_accuracy": 0.10,
            "stability_bonus": 0.05,
        },
        "total_evaluated": len(scored),
    }


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


@router.get("/analysis")
async def get_model_analysis():
    """返回最佳模型分析报告"""
    p = os.path.join(_RESULTS_DIR, "model_analysis.json")
    if os.path.isfile(p):
        with open(p) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="分析报告未生成，请先运行 pipeline")


@router.get("/correlation")
async def get_correlation_matrix():
    """计算股票收益率相关性矩阵"""
    import pandas as pd
    import numpy as np
    raw_dir = os.path.join(_DATA_DIR, "raw")

    symbols = []
    returns_dict = {}

    if os.path.isdir(raw_dir):
        for f in sorted(os.listdir(raw_dir)):
            if f.startswith("cn_") and f.endswith(".csv") and "idx_" not in f:
                sym = f.replace("cn_", "").replace(".csv", "")
                try:
                    df = pd.read_csv(os.path.join(raw_dir, f))
                    rets = df['close'].pct_change().dropna().tolist()
                    if rets:
                        symbols.append(sym)
                        returns_dict[sym] = rets
                except Exception:
                    pass

    if len(symbols) < 2:
        return {"xLabels": [], "yLabels": [], "values": []}

    min_len = min(len(v) for v in returns_dict.values())
    data = np.array([returns_dict[s][-min_len:] for s in symbols])
    corr = np.corrcoef(data)

    values = []
    for x in range(len(symbols)):
        for y in range(len(symbols)):
            values.append([x, y, round(float(corr[y][x]), 4)])

    return {"xLabels": symbols, "yLabels": symbols, "values": values}


def _find_equity_curve(model_id: str) -> Optional[str]:
    p = os.path.join(_RESULTS_DIR, "equity_curves", f"{model_id}.json")
    return p if os.path.isfile(p) else None


@router.get("/{model_id}/equity-curve")
async def get_equity_curve(model_id: str):
    """获取模型的每日资金曲线"""
    path = _find_equity_curve(model_id)
    if not path:
        raise HTTPException(status_code=404, detail=f"未找到 {model_id} 的资金曲线数据")
    with open(path) as f:
        data = json.load(f)
    # 对齐 dates 和 portfolio_values 长度，取较短的
    dates = data.get("dates", [])
    pv = data.get("portfolio_values", [])
    bv = data.get("benchmark_values", [])
    n = min(len(dates), len(pv))
    data["dates"] = dates[:n]
    data["portfolio_values"] = pv[:n]
    if bv:
        data["benchmark_values"] = bv[:n]
    return data


@router.get("/{model_id}")
async def get_backtest_by_model(model_id: str):
    """获取指定模型的回测结果"""
    all_results = _load_all_results()
    for i, row in enumerate(all_results):
        if row.get("model_id") == model_id:
            return _format_result(row, i + 1)
    raise HTTPException(status_code=404, detail=f"未找到模型 {model_id} 的回测结果")
