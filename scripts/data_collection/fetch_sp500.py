"""
批量下载 S&P 500 全部成分股历史日线数据

用法:
    python scripts/data_collection/fetch_sp500.py
    python scripts/data_collection/fetch_sp500.py --start 2016-01-01 --delay 0.5
    python scripts/data_collection/fetch_sp500.py --no-resume   # 强制重新下载
"""
import argparse
import sys
import time
from pathlib import Path
from datetime import date

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "data_collection"))

from fetch_stock_data import fetch_us_stock, save_stock, DATA_RAW_DIR


def get_sp500_symbols() -> list[str]:
    """从 Wikipedia 抓取当前 S&P 500 成分股列表"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    print(f"从 Wikipedia 获取 S&P 500 成分股列表...")
    try:
        tables = pd.read_html(url)
        df = tables[0]
        symbols = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"  获取到 {len(symbols)} 只成分股")
        return symbols
    except Exception as e:
        print(f"  Wikipedia 抓取失败: {e}")
        print(f"  使用备用方案: 从 yfinance 获取...")
        try:
            import yfinance as yf
            sp500 = yf.Ticker("^GSPC")
            # fallback: 手动维护的核心列表
            raise RuntimeError("yfinance 不直接提供成分股列表")
        except Exception:
            print("  备用方案也失败，使用内置核心列表")
            return _fallback_symbols()


def _fallback_symbols() -> list[str]:
    """内置的 S&P 500 核心股票（前 50 大权重股）"""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "GOOG", "BRK-B",
        "LLY", "AVGO", "JPM", "TSLA", "UNH", "XOM", "V", "PG", "MA",
        "COST", "JNJ", "HD", "MRK", "ABBV", "WMT", "NFLX", "BAC", "CRM",
        "CVX", "KO", "AMD", "PEP", "LIN", "TMO", "ORCL", "ACN", "MCD",
        "CSCO", "ADBE", "ABT", "WFC", "DHR", "GE", "TXN", "PM", "QCOM",
        "INTU", "CMCSA", "DIS", "VZ", "AMGN", "IBM",
    ]


def fetch_sp500(start: str = "2016-01-01", end: str | None = None,
                delay: float = 0.3, resume: bool = True):
    """批量下载 S&P 500 全部成分股"""
    symbols = get_sp500_symbols()
    end = end or date.today().isoformat()

    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    total = len(symbols)
    success = 0
    skipped = 0
    failed = []

    print(f"\n{'='*60}")
    print(f"S&P 500 批量下载: {total} 只股票, {start} → {end}")
    print(f"{'='*60}\n")

    for i, symbol in enumerate(symbols, 1):
        csv_path = DATA_RAW_DIR / f"us_{symbol}.csv"

        # 断点续传：跳过已有且数据充足的文件
        if resume and csv_path.exists():
            existing = pd.read_csv(csv_path)
            if len(existing) >= 1000:
                skipped += 1
                print(f"  [{i}/{total}] {symbol} 已存在 ({len(existing)} 条), 跳过")
                continue

        try:
            df = fetch_us_stock(symbol, start, end)
            if not df.empty:
                save_stock(df, symbol, market="us")
                success += 1
            else:
                failed.append(symbol)
        except Exception as e:
            print(f"  [{i}/{total}] {symbol} 失败: {e}")
            failed.append(symbol)

        if delay > 0 and i < total:
            time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"下载完成: 成功 {success}, 跳过 {skipped}, 失败 {len(failed)}")
    if failed:
        print(f"失败列表: {', '.join(failed)}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="批量下载 S&P 500 成分股数据")
    parser.add_argument("--start", default="2016-01-01", help="起始日期 (默认 2016-01-01)")
    parser.add_argument("--end", default=None, help="结束日期 (默认今天)")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔秒数 (默认 0.3)")
    parser.add_argument("--no-resume", action="store_true", help="不跳过已有文件，全部重新下载")
    args = parser.parse_args()

    fetch_sp500(
        start=args.start,
        end=args.end,
        delay=args.delay,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
