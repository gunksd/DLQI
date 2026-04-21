"""
数据同步服务 — yfinance 下载 + PostgreSQL 存储
"""

import os
import pandas as pd
from datetime import datetime
from typing import Callable, List
from loguru import logger

from app.core.config import settings


def run_data_sync(params: dict, progress_cb: Callable) -> dict:
    """
    数据同步任务（在线程池中执行）
    params: {symbols: [...]}
    """
    import yfinance as yf

    symbols: List[str] = params.get("symbols", [])
    if not symbols:
        raise ValueError("请指定要同步的股票代码")

    results = []
    total = len(symbols)

    for i, symbol in enumerate(symbols):
        pct = int(10 + 80 * i / total)
        progress_cb(pct, f"下载 {symbol} ({i+1}/{total})")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5y", auto_adjust=True).reset_index()
            df = df.rename(columns={
                "Date": "date", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume",
            })
            df["date"] = df["date"].dt.tz_localize(None)

            if df.empty:
                results.append({"symbol": symbol, "status": "failed", "error": "无数据"})
                continue

            # 保存到 CSV（与现有管道兼容）
            raw_dir = os.path.join(settings.DATA_DIR, "raw")
            os.makedirs(raw_dir, exist_ok=True)
            csv_path = os.path.join(raw_dir, f"us_{symbol}.csv")
            df.to_csv(csv_path, index=False)

            # 写入 PostgreSQL
            _save_to_postgres(symbol, df)

            results.append({
                "symbol": symbol,
                "status": "success",
                "records": len(df),
            })
        except Exception as e:
            logger.error(f"同步 {symbol} 失败: {e}")
            results.append({"symbol": symbol, "status": "failed", "error": str(e)})

    progress_cb(100, "同步完成")
    success = sum(1 for r in results if r["status"] == "success")
    return {"total": total, "success": success, "results": results}


def _save_to_postgres(symbol: str, df: pd.DataFrame):
    """将数据写入 PostgreSQL（同步方式，因为在线程中执行）"""
    import psycopg

    conn = psycopg.connect(settings.DATABASE_URL)
    cur = conn.cursor()

    cur.execute("DELETE FROM stock_data WHERE symbol = %s", (symbol,))

    rows = []
    for _, row in df.iterrows():
        date_val = row.get("date")
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.strftime("%Y-%m-%d")
        rows.append((
            symbol,
            str(date_val)[:10],
            float(row.get("open", 0)),
            float(row.get("high", 0)),
            float(row.get("low", 0)),
            float(row.get("close", 0)),
            float(row.get("volume", 0)),
        ))

    cur.executemany(
        "INSERT INTO stock_data (symbol, date, open, high, low, close, volume) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        rows,
    )
    conn.commit()
    conn.close()
    logger.info(f"PostgreSQL 已更新 {symbol}: {len(rows)} 条")


def get_synced_stocks() -> list:
    """从 PostgreSQL 查询已同步的股票列表"""
    import psycopg

    try:
        conn = psycopg.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT symbol, COUNT(*) as records,
                   MIN(date) as first_date, MAX(date) as last_date
            FROM stock_data
            GROUP BY symbol
            ORDER BY symbol
        """)
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "symbol": r[0],
                "records": r[1],
                "first_date": str(r[2])[:10] if r[2] else None,
                "last_date": str(r[3])[:10] if r[3] else None,
                "status": "updated",
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"查询股票列表失败: {e}")
        return []
