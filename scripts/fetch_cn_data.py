#!/usr/bin/env python3
"""
拉取 A 股历史数据（AKShare）
用法: cd /home/awan/DLQI && backend/venv/bin/python scripts/fetch_cn_data.py
"""

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STOCKS = {
    "600519": "贵州茅台",
    "601318": "中国平安",
    "600036": "招商银行",
    "300750": "宁德时代",
    "002594": "比亚迪",
}

START_DATE = "20160101"
END_DATE = datetime.now().strftime("%Y%m%d")


def fetch_stock(symbol: str, name: str):
    print(f"  拉取 {symbol} ({name}) ... ", end="", flush=True)
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=START_DATE,
        end_date=END_DATE,
        adjust="qfq",
    )
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    csv_path = RAW_DIR / f"cn_{symbol}.csv"
    df.to_csv(csv_path, index=False)
    print(f"{len(df)} 条 ({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")
    return len(df)


def main():
    print("=" * 60)
    print("DLQI: 拉取 A 股历史数据 (AKShare)")
    print(f"时间范围: {START_DATE[:4]}-{START_DATE[4:6]} ~ {END_DATE[:4]}-{END_DATE[4:6]}")
    print("=" * 60)

    total = 0
    for symbol, name in STOCKS.items():
        try:
            total += fetch_stock(symbol, name)
        except Exception as e:
            print(f"失败: {e}")

    print(f"\n完成! 共 {total} 条数据, 保存到 {RAW_DIR}")


if __name__ == "__main__":
    main()
