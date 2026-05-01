"""
机器学习模型管理 API — 使用真实模型数据
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.job_service import job_service

router = APIRouter()

# 延迟导入避免循环依赖
_manager = None

def _get_manager():
    global _manager
    if _manager is None:
        from app.services.model_service import model_manager
        _manager = model_manager
    return _manager


# ==================== 请求模型 ====================

class ModelConfig(BaseModel):
    name: str
    model_type: str
    params: Optional[Dict[str, Any]] = None


class TrainRequest(BaseModel):
    symbol: str
    model_type: str = "lightgbm"   # lightgbm, xgboost, lstm, transformer
    sequence_length: int = 60
    epochs: int = 50


class MultiTrainRequest(BaseModel):
    model_type: str = "transformer"
    sequence_length: int = 60
    epochs: int = 30
    max_stocks: Optional[int] = None


# ==================== API 端点 ====================

@router.get("/")
async def get_models(
    symbol: Optional[str] = None,
    model_type: Optional[str] = None,
):
    """获取所有模型列表，可按 symbol / model_type 筛选"""
    mgr = _get_manager()
    if symbol:
        items = mgr.list_by_symbol(symbol)
    elif model_type:
        items = mgr.list_by_type(model_type)
    else:
        items = mgr.list_models()
    return {"items": items, "total": len(items)}


@router.get("/symbols")
async def get_symbols():
    """获取所有有模型的股票代码"""
    mgr = _get_manager()
    return {"symbols": mgr.get_symbols()}


@router.get("/types")
async def get_model_types():
    """获取所有模型类型"""
    mgr = _get_manager()
    return {"types": mgr.get_model_types()}


@router.get("/compare")
async def compare_models(
    symbol: Optional[str] = None,
):
    """对比同一股票的不同模型，结合回测结果"""
    mgr = _get_manager()
    import os, csv
    results_path = os.path.join(os.getenv("DATA_DIR", "../data"), "..", "results", "backtest_results.csv")
    # 尝试多个可能路径
    for p in [results_path,
              "../results/backtest_results.csv",
              "./results/backtest_results.csv",
              "/app/results/backtest_results.csv"]:
        if os.path.isfile(p):
            results_path = p
            break

    backtest_data = {}
    if os.path.isfile(results_path):
        with open(results_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                backtest_data[row.get('model_id', '')] = row

    models = mgr.list_by_symbol(symbol) if symbol else mgr.list_models()
    comparison = []
    for m in models:
        mid = m['model_id']
        bt = backtest_data.get(mid, {})
        comparison.append({
            "model_id": mid,
            "name": m['name'],
            "model_type": m['model_type'],
            "symbol": m['symbol'],
            "val_loss": m.get('val_loss'),
            "total_return": _safe_float(bt.get('total_return')),
            "annual_return": _safe_float(bt.get('annual_return')),
            "sharpe_ratio": _safe_float(bt.get('sharpe_ratio')),
            "max_drawdown": _safe_float(bt.get('max_drawdown')),
            "direction_accuracy": _safe_float(bt.get('direction_accuracy')),
            "win_rate": _safe_float(bt.get('win_rate')),
            "profit_factor": _safe_float(bt.get('profit_factor')),
            "benchmark_return": _safe_float(bt.get('benchmark_return')),
            "excess_return": _safe_float(bt.get('excess_return')),
        })
    return {"models": comparison}


@router.get("/refresh")
async def refresh_models():
    """重新扫描模型目录"""
    mgr = _get_manager()
    mgr.refresh()
    return {"message": "模型列表已刷新", "total": len(mgr.list_models())}


@router.get("/{model_id}")
async def get_model(model_id: str):
    """获取单个模型详情"""
    mgr = _get_manager()
    info = mgr.get_model_info(model_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 未找到")
    return info


@router.get("/{model_id}/feature-importance")
async def get_feature_importance(model_id: str):
    """获取特征重要性"""
    mgr = _get_manager()
    features = mgr.get_feature_importance(model_id)
    if features is None:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 未找到")
    return {"model_id": model_id, "features": features}


@router.get("/{model_id}/predictions")
async def get_predictions(
    model_id: str,
    days: int = Query(60, ge=10, le=500),
    symbol: Optional[str] = Query(None, description="股票代码（MULTI模型必填）"),
):
    """用真实模型生成预测"""
    mgr = _get_manager()
    info = mgr.get_model_info(model_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 未找到")

    target_symbol = symbol or info['symbol']
    if target_symbol == "MULTI":
        raise HTTPException(status_code=400, detail="MULTI模型需要指定 symbol 参数，如 ?symbol=600519")

    # 获取数据
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(
            symbol=target_symbol, period="daily",
            start_date="20230101",
            end_date=__import__('datetime').datetime.now().strftime("%Y%m%d"),
            adjust="qfq",
        )
        df = df.rename(columns={
            '日期': 'date', '开盘': 'open', '最高': 'high',
            '最低': 'low', '收盘': 'close', '成交量': 'volume'
        })
        df['date'] = df['date'].dt.tz_localize(None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据失败: {e}")

    # 预测
    try:
        result = mgr.predict(model_id, df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    # 只返回最近 days 天
    n = min(days, len(result['predictions']))
    preds = result['predictions'][-n:]
    dates = result['dates'][-n:]
    dirs = result['directions'][-n:]
    prices = result['close_prices'][-n:]

    # 计算方向准确率
    correct = 0
    total = 0
    for i in range(1, len(preds)):
        actual_dir = 'up' if prices[i] > prices[i - 1] else 'down'
        if dirs[i - 1] == actual_dir:
            correct += 1
        total += 1

    predictions_list = []
    for i in range(len(preds)):
        predictions_list.append({
            "date": dates[i],
            "predicted_return": round(preds[i], 6),
            "direction": dirs[i],
            "close_price": round(prices[i], 2),
        })

    return {
        "model_id": model_id,
        "symbol": target_symbol,
        "predictions": predictions_list,
        "direction_accuracy": round(correct / total, 4) if total > 0 else 0,
        "total": len(predictions_list),
    }


# ==================== 训练 API ====================

@router.post("/train")
async def train_model(req: TrainRequest):
    """触发模型训练"""
    from app.services.training_service import run_training

    job_id = await job_service.submit(
        job_type="train",
        func=run_training,
        params={
            "symbol": req.symbol,
            "model_type": req.model_type,
            "sequence_length": req.sequence_length,
            "epochs": req.epochs,
        },
    )
    return {
        "message": f"训练任务已提交: {req.model_type} on {req.symbol}",
        "job_id": job_id,
    }


@router.post("/train-multi")
async def train_multi_stock(req: MultiTrainRequest):
    """触发多股票联合训练"""
    from app.services.training_service import run_multi_stock_training

    job_id = await job_service.submit(
        job_type="train_multi",
        func=run_multi_stock_training,
        params={
            "model_type": req.model_type,
            "sequence_length": req.sequence_length,
            "epochs": req.epochs,
            "max_stocks": req.max_stocks,
        },
    )
    return {
        "message": f"多股票联合训练已提交: {req.model_type}",
        "job_id": job_id,
    }


def _safe_float(val) -> Optional[float]:
    if val is None or val == '':
        return None
    try:
        v = float(val)
        if v != v or v == float('inf') or v == float('-inf'):
            return None
        return round(v, 6)
    except (ValueError, TypeError):
        return None
