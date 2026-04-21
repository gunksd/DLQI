"""
模拟交易 API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services import paper_trading_service as pts

router = APIRouter()


class CreatePortfolioRequest(BaseModel):
    name: str = "默认组合"
    initial_capital: float = 100000
    model_id: str = ""


class DeployStrategyRequest(BaseModel):
    model_id: str
    initial_capital: float = 100000
    days: int = 120


@router.post("/portfolios/from-strategy")
async def deploy_strategy(req: DeployStrategyRequest):
    """从推荐策略一键创建组合并运行历史模拟"""
    try:
        portfolio = pts.create_portfolio(
            name=f"主策略·{req.model_id}",
            initial_capital=req.initial_capital,
            model_id=req.model_id,
        )
        pid = portfolio["id"]
        result = pts.simulate_history(pid, req.days)
        return {"portfolio": portfolio, "simulation": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios")
async def list_portfolios():
    """列出所有模拟交易组合"""
    items = pts.list_portfolios()
    return {"items": items, "total": len(items)}


@router.post("/portfolios")
async def create_portfolio(req: CreatePortfolioRequest):
    """创建模拟交易组合"""
    result = pts.create_portfolio(req.name, req.initial_capital, req.model_id)
    return result


@router.get("/portfolios/{pid}")
async def get_portfolio(pid: str):
    """获取组合详情"""
    p = pts.get_portfolio(pid)
    if not p:
        raise HTTPException(status_code=404, detail="组合不存在")
    return p


@router.post("/portfolios/{pid}/run")
async def run_daily(pid: str):
    """执行一次每日更新"""
    try:
        result = pts.run_daily_update(pid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolios/{pid}/simulate")
async def simulate_history(pid: str, days: int = Query(120, ge=30, le=365)):
    """历史模拟：使用历史数据回放完整交易过程"""
    try:
        result = pts.simulate_history(pid, days)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/{pid}/trades")
async def get_trades(pid: str):
    """获取交易记录"""
    trades = pts.get_trades(pid)
    return {"items": trades, "total": len(trades)}


@router.get("/portfolios/{pid}/equity")
async def get_equity(pid: str):
    """获取权益曲线"""
    curve = pts.get_equity_curve(pid)
    return {"data": curve}


@router.delete("/portfolios/{pid}")
async def close_portfolio(pid: str):
    """平仓并关闭组合"""
    try:
        result = pts.close_portfolio(pid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
