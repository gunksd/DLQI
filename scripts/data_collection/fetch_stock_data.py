"""
数据获取脚本 - 从 akshare 拉取 A 股历史行情

用法:
    # 获取配置文件中所有 A 股
    python scripts/data_collection/fetch_stock_data.py

    # 获取单只 A 股
    python scripts/data_collection/fetch_stock_data.py --symbol 600519 --start 2016-01-01

    # 仅检查已有数据质量
    python scripts/data_collection/fetch_stock_data.py --check
"""
import argparse
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
CONFIG_PATH = PROJECT_ROOT / "config" / "stocks.yaml"


def fetch_cn_stock(code: str, start: str, end: str | None = None) -> pd.DataFrame:
    """通过 akshare 获取 A 股日线数据（前复权）"""
    import akshare as ak

    end = end or date.today().isoformat()
    start_fmt = start.replace("-", "")
    end_fmt = end.replace("-", "")

    print(f"  [akshare]  {code}  {start} → {end} ...", end=" ", flush=True)

    try:
        df = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_fmt, end_date=end_fmt, adjust="hfq",
        )
    except Exception as e:
        print(f"失败: {e}")
        return pd.DataFrame()

    if df.empty:
        print("无数据")
        return pd.DataFrame()

    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    print(f"OK {len(df)} 条")
    return df


def save_stock(df: pd.DataFrame, symbol: str):
    if df.empty:
        return
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_RAW_DIR / f"cn_{symbol}.csv"
    df.to_csv(filepath, index=False)
    print(f"    → 已保存 {filepath}  ({len(df)} 行)")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_all(config: dict):
    dr = config.get("date_range", {})
    start = dr.get("start", "2016-01-01")
    end = dr.get("end")

    stocks = config.get("cn_stocks", [])
    print(f"\n{'='*50}")
    print(f"A 股数据获取  ({len(stocks)} 只)")
    print(f"{'='*50}")

    for item in stocks:
        code = str(item["symbol"])
        df = fetch_cn_stock(code, start, end)
        save_stock(df, code)


def check_data_quality():
    print(f"\n{'='*50}")
    print("数据质量检查")
    print(f"{'='*50}")

    csv_files = sorted(DATA_RAW_DIR.glob("cn_*.csv"))
    if not csv_files:
        print("未发现任何数据文件")
        return

    summary = []
    for f in csv_files:
        df = pd.read_csv(f, parse_dates=["date"])
        summary.append({
            "文件": f.name, "行数": len(df),
            "起始": df["date"].min().strftime("%Y-%m-%d"),
            "结束": df["date"].max().strftime("%Y-%m-%d"),
            "缺失值": df.isnull().sum().sum(),
            "close均值": round(df["close"].mean(), 2),
        })

    report = pd.DataFrame(summary)
    print(report.to_string(index=False))
    print(f"\n共 {len(csv_files)} 个文件, 总计 {report['行数'].sum()} 条记录")


def main():
    parser = argparse.ArgumentParser(description="DLQI A 股数据获取工具")
    parser.add_argument("--symbol", type=str, help="A 股代码 (如 600519)")
    parser.add_argument("--start", type=str, default="2016-01-01", help="起始日期")
    parser.add_argument("--end", type=str, default=None, help="结束日期 (默认今天)")
    parser.add_argument("--check", action="store_true", help="仅检查已有数据质量")
    args = parser.parse_args()

    if args.check:
        check_data_quality()
        return

    if args.symbol:
        df = fetch_cn_stock(args.symbol, args.start, args.end)
        save_stock(df, args.symbol)
        check_data_quality()
        return

    config = load_config()
    fetch_all(config)
    check_data_quality()


if __name__ == "__main__":
    main()
