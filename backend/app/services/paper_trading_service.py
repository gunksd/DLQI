"""
模拟交易服务 — 虚拟组合管理（PostgreSQL）
"""

import uuid
import json
from datetime import datetime
from typing import Optional
from loguru import logger

from app.core.config import settings


def _conn():
    import psycopg
    return psycopg.connect(settings.DATABASE_URL)


def create_portfolio(name: str, initial_capital: float, model_id: str = "", symbol: str = "", config: dict = None) -> dict:
    pid = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO paper_portfolios (id, name, initial_capital, cash, positions, total_value, model_id, status, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (pid, name, initial_capital, initial_capital, json.dumps({}), initial_capital, model_id, "active", now, now),
        )
    return {"id": pid, "name": name, "initial_capital": initial_capital, "cash": initial_capital,
            "positions": {}, "total_value": initial_capital, "model_id": model_id, "status": "active"}


def get_portfolio(pid: str) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.execute("SELECT id,name,initial_capital,cash,positions,total_value,model_id,status,created_at,updated_at FROM paper_portfolios WHERE id=%s", (pid,))
        row = cur.fetchone()
    if not row:
        return None
    cols = ["id","name","initial_capital","cash","positions","total_value","model_id","status","created_at","updated_at"]
    d = dict(zip(cols, row))
    if isinstance(d["positions"], str):
        d["positions"] = json.loads(d["positions"])
    return d


def list_portfolios() -> list:
    with _conn() as conn:
        cur = conn.execute(
            "SELECT id,name,initial_capital,cash,total_value,model_id,status,created_at FROM paper_portfolios ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
    return [{"id": r[0],"name": r[1],"initial_capital": r[2],"cash": r[3],
             "total_value": r[4],"model_id": r[5],"status": r[6],"created_at": str(r[7])} for r in rows]


def get_trades(pid: str) -> list:
    with _conn() as conn:
        cur = conn.execute(
            "SELECT id,symbol,side,quantity,price,commission,signal_source,timestamp FROM paper_trades WHERE portfolio_id=%s ORDER BY timestamp DESC",
            (pid,),
        )
        rows = cur.fetchall()
    return [{"id": r[0],"symbol": r[1],"side": r[2],"quantity": r[3],
             "price": r[4],"commission": r[5],"signal_source": r[6],"timestamp": str(r[7])} for r in rows]


def get_equity_curve(pid: str) -> list:
    portfolio = get_portfolio(pid)
    if not portfolio:
        return []
    with _conn() as conn:
        cur = conn.execute(
            "SELECT timestamp,side,quantity,price,commission FROM paper_trades WHERE portfolio_id=%s ORDER BY timestamp",
            (pid,),
        )
        trades = cur.fetchall()
    curve = [{"date": str(portfolio["created_at"])[:10], "value": portfolio["initial_capital"]}]
    for t in trades:
        ts, side, qty, price, commission = t
        curve.append({"date": str(ts)[:10], "value": portfolio["total_value"]})
    return curve


def delete_portfolio(pid: str):
    with _conn() as conn:
        conn.execute("DELETE FROM paper_trades WHERE portfolio_id=%s", (pid,))
        conn.execute("DELETE FROM paper_portfolios WHERE id=%s", (pid,))


def close_portfolio(pid: str) -> dict:
    delete_portfolio(pid)
    return {"id": pid, "status": "closed"}


def run_daily_update(pid: str) -> dict:
    portfolio = get_portfolio(pid)
    if not portfolio:
        raise ValueError("组合不存在")
    return {"id": pid, "status": portfolio["status"], "message": "已更新"}


def simulate_history(pid: str, days: int = 120) -> dict:
    """历史模拟：使用历史数据回放模型交易过程"""
    import numpy as np
    import pandas as pd

    portfolio = get_portfolio(pid)
    if not portfolio or portfolio["status"] != "active":
        raise ValueError("组合不存在或已关闭")

    model_id = portfolio.get("model_id", "")
    if not model_id:
        raise ValueError("组合未关联模型，无法进行历史模拟")

    from app.services.model_service import model_manager
    model_info = model_manager.get_model_info(model_id)
    if not model_info:
        raise ValueError(f"模型 {model_id} 不存在")

    symbol = model_info["symbol"]

    # 优先使用本地 CSV 数据，避免网络依赖
    import os
    from app.core.config import settings
    target_symbol = symbol
    if symbol == "MULTI":
        target_symbol = settings.STOCK_POOL[0]  # 默认用第一只股票

    csv_path = os.path.join(settings.DATA_DIR, "raw", f"cn_{target_symbol}.csv")
    if os.path.isfile(csv_path):
        hist = pd.read_csv(csv_path)
    else:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=target_symbol, period="daily", start_date="20160101", adjust="hfq")
        df = df.rename(columns={"日期":"date","开盘":"open","最高":"high","最低":"low","收盘":"close","成交量":"volume"})
        hist = df[["date","open","high","low","close","volume"]].copy()

    if len(hist) < 100:
        raise ValueError(f"历史数据不足: 仅 {len(hist)} 条")

    result = model_manager.predict(model_id, hist)
    predictions = result["predictions"]
    pred_dates = result["dates"]
    close_prices = result["close_prices"]

    if len(predictions) < days:
        days = len(predictions)

    start_idx = max(0, len(predictions) - days)
    sim_preds = predictions[start_idx:]
    sim_dates = pred_dates[start_idx:]
    sim_prices = close_prices[start_idx:]

    pred_arr = np.array(sim_preds)
    threshold = float(np.median(pred_arr))

    initial_capital = portfolio["initial_capital"]
    cash = initial_capital
    positions = {}
    equity_curve = []
    all_trades = []
    commission_rate = 0.001

    for i in range(len(sim_preds)):
        date_str = str(sim_dates[i])[:10]
        pred = sim_preds[i]
        price = sim_prices[i]
        signal = "buy" if pred > threshold else "sell"

        if signal == "buy" and symbol not in positions:
            buy_amount = cash * 0.3
            qty = int(buy_amount / price)
            if qty > 0:
                cost = qty * price
                commission = cost * commission_rate
                cash -= (cost + commission)
                positions[symbol] = {"qty": qty, "avg_price": price}
                all_trades.append({"date": date_str, "side": "buy", "symbol": symbol,
                                   "qty": qty, "price": round(price, 2), "commission": round(commission, 2)})

        elif signal == "sell" and symbol in positions:
            pos = positions[symbol]
            qty = pos["qty"]
            revenue = qty * price
            commission = revenue * commission_rate
            cash += (revenue - commission)
            del positions[symbol]
            all_trades.append({"date": date_str, "side": "sell", "symbol": symbol,
                               "qty": qty, "price": round(price, 2), "commission": round(commission, 2)})

        pos_value = sum(p["qty"] * sim_prices[i] for p in positions.values())
        equity_curve.append({"date": date_str, "value": round(cash + pos_value, 2)})

    pos_value = sum(p["qty"] * sim_prices[-1] for p in positions.values()) if positions else 0
    final_value = round(cash + pos_value, 2)
    now = datetime.utcnow().isoformat()

    # 写入交易记录
    with _conn() as conn:
        conn.execute("DELETE FROM paper_trades WHERE portfolio_id=%s", (pid,))
        for t in all_trades:
            conn.execute(
                "INSERT INTO paper_trades (portfolio_id,symbol,side,quantity,price,commission,signal_source,timestamp) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (pid, t["symbol"], t["side"], t["qty"], t["price"], t["commission"], f"model:{model_id}", t["date"]),
            )
        conn.execute(
            "UPDATE paper_portfolios SET cash=%s,positions=%s,total_value=%s,updated_at=%s WHERE id=%s",
            (cash, json.dumps(positions), final_value, now, pid),
        )

    # benchmark
    benchmark = []
    if len(sim_prices) > 0:
        b0 = sim_prices[0]
        benchmark = [{"date": str(sim_dates[i])[:10], "value": round(initial_capital * sim_prices[i] / b0, 2)} for i in range(len(sim_prices))]

    return {
        "symbol": symbol, "model_id": model_id, "days": len(equity_curve),
        "equity_curve": equity_curve, "benchmark": benchmark, "trades": all_trades,
        "initial_capital": initial_capital, "final_value": final_value,
        "pnl": round(final_value - initial_capital, 2),
        "pnl_pct": round((final_value / initial_capital - 1) * 100, 2),
        "n_trades": len(all_trades),
    }
