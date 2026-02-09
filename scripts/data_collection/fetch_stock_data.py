"""
数据获取脚本 - 从 yfinance / akshare 拉取股票历史行情

用法:
    # 获取配置文件中所有股票
    python scripts/data_collection/fetch_stock_data.py

    # 获取单只美股
    python scripts/data_collection/fetch_stock_data.py --symbol AAPL --start 2020-01-01

    # 获取单只A股
    python scripts/data_collection/fetch_stock_data.py --symbol 600519 --market cn --start 2020-01-01

    # 指定结束日期
    python scripts/data_collection/fetch_stock_data.py --symbol AAPL --start 2020-01-01 --end 2024-12-31

    # 只获取美股 / 只获取A股
    python scripts/data_collection/fetch_stock_data.py --us-only
    python scripts/data_collection/fetch_stock_data.py --cn-only
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import numpy as np
import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
CONFIG_PATH = PROJECT_ROOT / "config" / "stocks.yaml"


# ─── yfinance 美股获取 ───────────────────────────────────────────

def fetch_us_stock(symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
    """
    通过 yfinance 获取美股/指数日线数据

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, symbol
    """
    import yfinance as yf

    end = end or date.today().isoformat()
    print(f"  [yfinance] {symbol}  {start} → {end} ...", end=" ", flush=True)

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=True)

    if df.empty:
        print("无数据")
        return pd.DataFrame()

    df = df.reset_index()
    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    # 只保留需要的列
    keep_cols = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    # 确保 date 是日期格式 (去掉时区)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()

    # 添加标识列
    df["symbol"] = symbol

    # 涨跌幅
    df["pct_change"] = df["close"].pct_change() * 100

    print(f"✓ {len(df)} 条")
    return df


# ─── akshare A股获取 ─────────────────────────────────────────────

def fetch_cn_stock(code: str, start: str, end: str | None = None) -> pd.DataFrame:
    """
    通过 akshare 获取 A 股日线数据

    Args:
        code: 6位股票代码, 如 "600519"
        start: 起始日期 "2020-01-01"
        end:   结束日期

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, symbol
    """
    try:
        import akshare as ak
    except ImportError:
        print(f"  [akshare]  {code}  跳过 (akshare 未安装, 运行: pip install akshare)")
        return pd.DataFrame()

    end = end or date.today().isoformat()
    start_fmt = start.replace("-", "")
    end_fmt = end.replace("-", "")

    print(f"  [akshare]  {code}  {start} → {end} ...", end=" ", flush=True)

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_fmt,
            end_date=end_fmt,
            adjust="qfq",  # 前复权
        )
    except Exception as e:
        print(f"失败: {e}")
        return pd.DataFrame()

    if df.empty:
        print("无数据")
        return pd.DataFrame()

    # akshare 返回的列名是中文, 需要映射
    col_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "price_change",
        "换手率": "turnover",
    }
    df = df.rename(columns=col_map)

    keep_cols = ["date", "open", "high", "low", "close", "volume",
                 "amount", "pct_change", "turnover"]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = code

    print(f"✓ {len(df)} 条")
    return df


# ─── 保存逻辑 ────────────────────────────────────────────────────

def save_stock(df: pd.DataFrame, symbol: str, market: str = "us"):
    """保存单只股票数据为 CSV"""
    if df.empty:
        return

    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{market}_{symbol}.csv"
    filepath = DATA_RAW_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"    → 已保存 {filepath}  ({len(df)} 行)")


def load_config() -> dict:
    """加载股票池配置"""
    if not CONFIG_PATH.exists():
        print(f"配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─── 批量获取 ────────────────────────────────────────────────────

def fetch_all_us(config: dict):
    """批量获取所有美股"""
    dr = config.get("date_range", {})
    start = dr.get("start", "2020-01-01")
    end = dr.get("end")

    stocks = config.get("us_stocks", [])
    indices = [i for i in config.get("indices", []) if i.get("source") == "yfinance"]

    print(f"\n{'='*50}")
    print(f"美股数据获取  ({len(stocks)} 只股票 + {len(indices)} 个指数)")
    print(f"{'='*50}")

    for item in stocks:
        symbol = item["symbol"]
        df = fetch_us_stock(symbol, start, end)
        save_stock(df, symbol, market="us")

    for item in indices:
        symbol = item["symbol"]
        df = fetch_us_stock(symbol, start, end)
        safe_name = symbol.replace("^", "idx_")
        save_stock(df, safe_name, market="us")


def fetch_all_cn(config: dict):
    """批量获取所有A股"""
    dr = config.get("date_range", {})
    start = dr.get("start", "2020-01-01")
    end = dr.get("end")

    stocks = config.get("cn_stocks", [])
    if not stocks:
        print("A股列表为空, 跳过")
        return

    print(f"\n{'='*50}")
    print(f"A股数据获取  ({len(stocks)} 只)")
    print(f"{'='*50}")

    for item in stocks:
        code = str(item["symbol"])
        df = fetch_cn_stock(code, start, end)
        save_stock(df, code, market="cn")


# ─── 数据质量检查 ─────────────────────────────────────────────────

def check_data_quality():
    """检查已下载数据的基本质量"""
    print(f"\n{'='*50}")
    print("数据质量检查")
    print(f"{'='*50}")

    csv_files = sorted(DATA_RAW_DIR.glob("*.csv"))
    if not csv_files:
        print("未发现任何数据文件")
        return

    summary = []
    for f in csv_files:
        df = pd.read_csv(f, parse_dates=["date"])
        row = {
            "文件": f.name,
            "行数": len(df),
            "起始": df["date"].min().strftime("%Y-%m-%d"),
            "结束": df["date"].max().strftime("%Y-%m-%d"),
            "缺失值": df.isnull().sum().sum(),
            "close均值": round(df["close"].mean(), 2),
        }
        summary.append(row)

    report = pd.DataFrame(summary)
    print(report.to_string(index=False))
    print(f"\n共 {len(csv_files)} 个文件, 总计 {report['行数'].sum()} 条记录")


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DLQI 股票数据获取工具")
    parser.add_argument("--symbol", type=str, help="单只股票代码 (如 AAPL 或 600519)")
    parser.add_argument("--market", type=str, default="us", choices=["us", "cn"],
                        help="市场: us=美股, cn=A股 (默认 us)")
    parser.add_argument("--start", type=str, default="2020-01-01", help="起始日期 (默认 2020-01-01)")
    parser.add_argument("--end", type=str, default=None, help="结束日期 (默认今天)")
    parser.add_argument("--us-only", action="store_true", help="只获取美股")
    parser.add_argument("--cn-only", action="store_true", help="只获取A股")
    parser.add_argument("--check", action="store_true", help="仅检查已有数据质量")

    args = parser.parse_args()

    # 仅检查
    if args.check:
        check_data_quality()
        return

    # 单只股票模式
    if args.symbol:
        if args.market == "cn":
            df = fetch_cn_stock(args.symbol, args.start, args.end)
            save_stock(df, args.symbol, market="cn")
        else:
            df = fetch_us_stock(args.symbol, args.start, args.end)
            save_stock(df, args.symbol, market="us")
        check_data_quality()
        return

    # 批量模式 (从配置文件读取)
    config = load_config()

    if args.cn_only:
        fetch_all_cn(config)
    elif args.us_only:
        fetch_all_us(config)
    else:
        fetch_all_us(config)
        fetch_all_cn(config)

    check_data_quality()


if __name__ == "__main__":
    main()
