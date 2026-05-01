"""
数据管理 API - AKShare + CSV
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import os

from app.services.job_service import job_service

# Compute absolute project root from this file's location
# __file__ = .../backend/app/api/data.py → project root = 3 levels up from backend/
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

try:
    from app.services.data.fetcher import OpenBBFetcher
    from app.services.data.cleaner import DataCleaner
    from app.services.features.indicators import TechnicalIndicators
except ImportError:
    OpenBBFetcher = None
    DataCleaner = None
    TechnicalIndicators = None


router = APIRouter()


# ==================== 请求/响应模型 ====================

class StockDataRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    provider: str = "akshare"  # akshare
    interval: str = "1d"  # 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1mo


class StockDataResponse(BaseModel):
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataSourceStatus(BaseModel):
    name: str
    type: str
    status: str
    last_sync: Optional[datetime]
    records: int
    size: str


class SyncTaskRequest(BaseModel):
    symbols: List[str]
    start_date: str
    end_date: str
    provider: str = "akshare"


class ScreenerRequest(BaseModel):
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    volume_min: Optional[float] = None
    limit: int = 100


# ==================== 数据获取器实例 ====================

def get_fetcher(provider: str = "yfinance") -> OpenBBFetcher:
    """获取数据获取器实例"""
    return OpenBBFetcher(provider=provider)


# ==================== API端点 ====================

@router.get("/sources")
async def get_data_sources():
    """获取数据源状态 — 基于真实文件"""
    raw_dir = os.path.join(_DATA_DIR, "raw")
    db_path = os.path.join(_DATA_DIR, "dlqi.db")
    models_dir = os.path.join(_DATA_DIR, "models")

    # Count CSV records
    csv_count = 0
    csv_size = 0
    if os.path.isdir(raw_dir):
        for f in os.listdir(raw_dir):
            fp = os.path.join(raw_dir, f)
            if f.endswith(".csv") and os.path.isfile(fp):
                csv_size += os.path.getsize(fp)
                try:
                    with open(fp) as fh:
                        csv_count += sum(1 for _ in fh) - 1  # minus header
                except Exception:
                    pass

    # SQLite size
    db_size = os.path.getsize(db_path) if os.path.isfile(db_path) else 0

    # Model files
    model_count = 0
    model_size = 0
    if os.path.isdir(models_dir):
        for root, _, files in os.walk(models_dir):
            for f in files:
                fp = os.path.join(root, f)
                model_size += os.path.getsize(fp)
                model_count += 1

    def fmt_size(b: int) -> str:
        if b > 1_000_000_000:
            return f"{b / 1_000_000_000:.1f} GB"
        if b > 1_000_000:
            return f"{b / 1_000_000:.1f} MB"
        return f"{b / 1_000:.1f} KB"

    sources = [
        {
            "name": "AKShare (CSV)",
            "type": "local_csv",
            "status": "connected" if csv_count > 0 else "empty",
            "last_sync": None,
            "records": csv_count,
            "size": fmt_size(csv_size),
            "description": "本地 CSV A 股历史价格数据",
        },
        {
            "name": "SQLite 数据库",
            "type": "database",
            "status": "connected" if os.path.isfile(db_path) else "disconnected",
            "last_sync": None,
            "records": 0,
            "size": fmt_size(db_size),
            "description": "本地 SQLite 存储",
        },
        {
            "name": "模型文件",
            "type": "models",
            "status": "available" if model_count > 0 else "empty",
            "last_sync": None,
            "records": model_count,
            "size": fmt_size(model_size),
            "description": "已训练模型权重",
        },
    ]
    return sources


@router.get("/providers")
async def get_providers():
    """获取可用的数据提供商列表"""
    return {
        "equity": ["akshare"],
        "index": ["akshare"],
        "etf": ["akshare"],
    }


@router.get("/stocks")
async def get_stocks(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取股票列表 — 优先 SQLite，回退硬编码"""
    from app.services.data_sync_service import get_synced_stocks
    synced = get_synced_stocks()

    if synced:
        stocks = [
            {
                "symbol": s["symbol"],
                "name": s["symbol"],
                "sector": "",
                "records": s["records"],
                "last_update": s["last_date"],
                "status": s["status"],
            }
            for s in synced
        ]
    else:
        # 回退：扫描本地 CSV
        raw_dir = os.path.join(_DATA_DIR, "raw")
        stocks = []
        if os.path.isdir(raw_dir):
            for f in sorted(os.listdir(raw_dir)):
                if f.endswith(".csv") and not f.startswith("idx_"):
                    sym = f.replace("cn_", "").replace(".csv", "")
                    stocks.append({
                        "symbol": sym, "name": sym, "sector": "",
                        "records": 0, "last_update": None, "status": "local",
                    })
        if not stocks:
            stocks = [
                {"symbol": "600519", "name": "贵州茅台", "sector": "白酒", "records": 0, "last_update": None, "status": "not_synced"},
                {"symbol": "601318", "name": "中国平安", "sector": "保险", "records": 0, "last_update": None, "status": "not_synced"},
                {"symbol": "600036", "name": "招商银行", "sector": "银行", "records": 0, "last_update": None, "status": "not_synced"},
                {"symbol": "300750", "name": "宁德时代", "sector": "新能源", "records": 0, "last_update": None, "status": "not_synced"},
                {"symbol": "002594", "name": "比亚迪", "sector": "汽车", "records": 0, "last_update": None, "status": "not_synced"},
            ]

    if search:
        stocks = [s for s in stocks if search.lower() in s["symbol"].lower() or search.lower() in s.get("name", "").lower()]

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": stocks[start:end],
        "total": len(stocks),
        "page": page,
        "page_size": page_size
    }


@router.get("/stocks/{symbol}")
async def get_stock_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d",
    provider: str = "akshare",
    limit: int = Query(500, ge=10, le=2000),
):
    """获取单只股票历史数据 — 优先本地 CSV，回退到 OpenBB"""
    df = None
    source = "local"

    # 方案1: 优先读取本地 CSV（与训练数据一致）
    for prefix in ["cn_", ""]:
        csv_path = os.path.join(_DATA_DIR, "raw", f"{prefix}{symbol}.csv")
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
            source = "local_csv"
            break

    # 方案2: 本地没有时使用 OpenBB
    if (df is None or (isinstance(df, pd.DataFrame) and df.empty)) and OpenBBFetcher is not None:
        try:
            fetcher = get_fetcher(provider)
            df = fetcher.fetch_historical(
                symbol,
                start_date or "2024-01-01",
                end_date or datetime.now().strftime("%Y-%m-%d"),
                interval=interval
            )
            source = provider
        except Exception:
            df = None

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的数据")

    # 统一列名
    col_map = {'Date': 'date', 'Open': 'open', 'High': 'high',
               'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 统一日期格式为 YYYY-MM-DD
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce').dt.strftime('%Y-%m-%d')
        if start_date:
            df = df[df['date'] >= start_date[:10]]
        if end_date:
            df = df[df['date'] <= end_date[:10]]

    df = df.fillna(0)
    data = df.tail(limit).to_dict(orient="records")

    for record in data:
        for key, value in record.items():
            if isinstance(value, (pd.Timestamp, datetime)):
                record[key] = str(value)[:10]
            elif isinstance(value, float) and (pd.isna(value) or np.isinf(value)):
                record[key] = 0

    return {
        "symbol": symbol,
        "provider": source,
        "interval": interval,
        "records": len(data),
        "data": data
    }


@router.get("/stocks/{symbol}/quote")
async def get_stock_quote(symbol: str, provider: str = "yfinance"):
    """获取股票实时报价 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        quote = fetcher.fetch_quote(symbol)

        if quote is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的报价")

        return quote

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}/profile")
async def get_stock_profile(symbol: str, provider: str = "yfinance"):
    """获取公司概况 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        profile = fetcher.fetch_profile(symbol)

        if profile is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的公司信息")

        return profile

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}/financials")
async def get_stock_financials(
    symbol: str,
    statement: str = Query("income", description="income, balance, cashflow"),
    period: str = Query("annual", description="annual, quarter"),
    provider: str = "akshare"
):
    """获取财务报表 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)

        if statement == "income":
            data = fetcher.fetch_income_statement(symbol, period)
        elif statement == "balance":
            data = fetcher.fetch_balance_sheet(symbol, period)
        elif statement == "cashflow":
            data = fetcher.fetch_cash_flow(symbol, period)
        else:
            raise HTTPException(status_code=400, detail="无效的报表类型")

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的财务数据")

        if isinstance(data, pd.DataFrame):
            data = data.reset_index().to_dict(orient="records")

        return {
            "symbol": symbol,
            "statement": statement,
            "period": period,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}/ratios")
async def get_stock_ratios(symbol: str, provider: str = "yfinance"):
    """获取财务比率 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        ratios = fetcher.fetch_ratios(symbol)

        if ratios is None or (isinstance(ratios, pd.DataFrame) and ratios.empty):
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的财务比率")

        if isinstance(ratios, pd.DataFrame):
            ratios = ratios.reset_index().to_dict(orient="records")

        return {
            "symbol": symbol,
            "ratios": ratios
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_data(request: SyncTaskRequest):
    """同步股票数据（异步任务）"""
    from app.services.data_sync_service import run_data_sync

    job_id = await job_service.submit(
        job_type="sync",
        func=run_data_sync,
        params={"symbols": request.symbols},
    )
    return {
        "status": "submitted",
        "job_id": job_id,
        "message": f"正在同步 {len(request.symbols)} 只股票",
    }


@router.get("/index/{symbol}")
async def get_index_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "akshare"
):
    """获取指数数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        df = fetcher.fetch_index_historical(
            symbol,
            start_date or "2024-01-01",
            end_date
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到指数 {symbol} 的数据")

        data = df.reset_index().to_dict(orient="records")

        for record in data:
            for key, value in record.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = value.isoformat()

        return {
            "symbol": symbol,
            "type": "index",
            "records": len(data),
            "data": data[-100:]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/{symbol}")
async def get_etf_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "akshare"
):
    """获取ETF数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        df = fetcher.fetch_etf_historical(
            symbol,
            start_date or "2024-01-01",
            end_date
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到ETF {symbol} 的数据")

        data = df.reset_index().to_dict(orient="records")

        for record in data:
            for key, value in record.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = value.isoformat()

        return {
            "symbol": symbol,
            "type": "etf",
            "records": len(data),
            "data": data[-100:]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/{symbol}/holdings")
async def get_etf_holdings(symbol: str, provider: str = "yfinance"):
    """获取ETF持仓 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        holdings = fetcher.fetch_etf_holdings(symbol)

        if holdings is None or (isinstance(holdings, pd.DataFrame) and holdings.empty):
            raise HTTPException(status_code=404, detail=f"未找到ETF {symbol} 的持仓数据")

        if isinstance(holdings, pd.DataFrame):
            holdings = holdings.to_dict(orient="records")

        return {
            "symbol": symbol,
            "holdings": holdings
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news")
async def get_news(
    symbols: Optional[str] = Query(None, description="逗号分隔的股票代码"),
    limit: int = Query(20, ge=1, le=100),
    provider: str = "akshare"
):
    """获取市场新闻 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        symbol_list = symbols.split(",") if symbols else None
        news = fetcher.fetch_news(symbol_list, limit)

        if news is None or (isinstance(news, pd.DataFrame) and news.empty):
            return {"news": [], "count": 0}

        if isinstance(news, pd.DataFrame):
            news = news.to_dict(orient="records")

        return {
            "symbols": symbol_list,
            "news": news,
            "count": len(news)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/economy/{indicator}")
async def get_economic_indicator(
    indicator: str,
    start_date: Optional[str] = None,
    provider: str = "fred"
):
    """获取宏观经济指标 (OpenBB - FRED)"""
    try:
        fetcher = get_fetcher(provider)
        df = fetcher.fetch_economic_indicator(
            indicator,
            start_date or "2020-01-01"
        )

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"未找到经济指标 {indicator}")

        data = df.reset_index().to_dict(orient="records")

        for record in data:
            for key, value in record.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = value.isoformat()

        return {
            "indicator": indicator,
            "provider": provider,
            "records": len(data),
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/economy/indicators")
async def get_common_indicators():
    """获取常用经济指标列表"""
    return {
        "indicators": [
            {"symbol": "GDP", "name": "国内生产总值", "category": "growth"},
            {"symbol": "UNRATE", "name": "失业率", "category": "employment"},
            {"symbol": "CPIAUCSL", "name": "消费者价格指数", "category": "inflation"},
            {"symbol": "FEDFUNDS", "name": "联邦基金利率", "category": "interest_rates"},
            {"symbol": "DGS10", "name": "10年期国债收益率", "category": "interest_rates"},
            {"symbol": "M2SL", "name": "M2货币供应量", "category": "money_supply"},
            {"symbol": "INDPRO", "name": "工业生产指数", "category": "production"},
            {"symbol": "UMCSENT", "name": "消费者信心指数", "category": "sentiment"},
            {"symbol": "HOUST", "name": "新屋开工数", "category": "housing"},
            {"symbol": "PAYEMS", "name": "非农就业人数", "category": "employment"},
        ]
    }


@router.get("/options/{symbol}")
async def get_options_chain(symbol: str, provider: str = "yfinance"):
    """获取期权链数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        options = fetcher.fetch_options_chains(symbol)

        if options is None or (isinstance(options, pd.DataFrame) and options.empty):
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的期权数据")

        if isinstance(options, pd.DataFrame):
            options = options.to_dict(orient="records")

        return {
            "symbol": symbol,
            "options": options
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screen")
async def screen_stocks(request: ScreenerRequest):
    """股票筛选器 (OpenBB)"""
    try:
        fetcher = get_fetcher("yfinance")
        results = fetcher.screen_stocks(
            market_cap_min=request.market_cap_min,
            market_cap_max=request.market_cap_max,
            sector=request.sector,
            industry=request.industry,
            price_min=request.price_min,
            price_max=request.price_max,
            volume_min=request.volume_min,
            limit=request.limit
        )

        if results is None or (isinstance(results, pd.DataFrame) and results.empty):
            return {"results": [], "count": 0}

        if isinstance(results, pd.DataFrame):
            results = results.to_dict(orient="records")

        return {
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_data_quality():
    """获取数据质量指标 — 基于真实 CSV 检查"""
    raw_dir = os.path.join(_DATA_DIR, "raw")
    total_rows = 0
    null_cells = 0
    total_cells = 0
    file_count = 0

    if os.path.isdir(raw_dir):
        for f in sorted(os.listdir(raw_dir)):
            if f.endswith(".csv"):
                try:
                    df = pd.read_csv(os.path.join(raw_dir, f))
                    total_rows += len(df)
                    total_cells += df.size
                    null_cells += int(df.isnull().sum().sum())
                    file_count += 1
                except Exception:
                    pass

    completeness = round((1 - null_cells / total_cells) * 100, 1) if total_cells else 0
    return {
        "completeness": completeness,
        "accuracy": completeness,  # same metric for CSV data
        "consistency": 100.0 if file_count > 0 else 0,
        "timeliness": 100.0 if file_count > 0 else 0,
        "overall": round(completeness, 1),
        "total_rows": total_rows,
        "files": file_count,
        "provider_status": {
            "local_csv": "healthy" if file_count > 0 else "empty",
        },
    }


@router.get("/storage")
async def get_storage_stats():
    """获取存储统计 — 基于真实文件大小"""
    def dir_size(path: str) -> int:
        total = 0
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    total += os.path.getsize(os.path.join(root, f))
        elif os.path.isfile(path):
            total = os.path.getsize(path)
        return total

    raw_size = dir_size(os.path.join(_DATA_DIR, "raw"))
    models_size = dir_size(os.path.join(_DATA_DIR, "models"))
    db_size = dir_size(os.path.join(_DATA_DIR, "dlqi.db"))
    results_size = dir_size(os.path.join(_PROJECT_ROOT, "results"))

    total = raw_size + models_size + db_size + results_size
    to_gb = lambda b: round(b / 1_000_000_000, 2)

    return {
        "total_size_gb": to_gb(total),
        "max_size_gb": 10.0,
        "items": [
            {"name": "价格数据 (CSV)", "size_gb": to_gb(raw_size), "color": "#00f5ff"},
            {"name": "模型文件", "size_gb": to_gb(models_size), "color": "#bf00ff"},
            {"name": "数据库", "size_gb": to_gb(db_size), "color": "#00ff88"},
            {"name": "回测结果", "size_gb": to_gb(results_size), "color": "#ffa502"},
        ],
    }


@router.get("/features/{symbol}")
async def get_features(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "akshare"
):
    """获取股票特征数据 (OpenBB + 技术指标)"""
    try:
        fetcher = get_fetcher(provider)
        indicator = TechnicalIndicators()

        df = fetcher.fetch_historical(
            symbol,
            start_date or "2024-01-01",
            end_date or datetime.now().strftime("%Y-%m-%d")
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的数据")

        df = indicator.calculate_all(df)

        data = df.tail(50).reset_index().to_dict(orient="records")

        for record in data:
            for key, value in record.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = value.isoformat()

        return {
            "symbol": symbol,
            "provider": provider,
            "features": list(df.columns),
            "feature_count": len(df.columns),
            "records": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch")
async def batch_fetch(
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "akshare"
):
    """批量获取多只股票数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        symbol_list = [s.strip() for s in symbols.split(",")]

        df = fetcher.fetch_multiple(
            symbol_list,
            start_date or "2024-01-01",
            end_date or datetime.now().strftime("%Y-%m-%d")
        )

        if df.empty:
            raise HTTPException(status_code=404, detail="未找到任何数据")

        result = {}
        for symbol in symbol_list:
            if symbol in df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else symbol in df.columns:
                symbol_df = df[symbol] if isinstance(df.columns, pd.MultiIndex) else df[[symbol]]
                symbol_data = symbol_df.tail(50).reset_index().to_dict(orient="records")
                result[symbol] = {
                    "records": len(symbol_data),
                    "data": symbol_data
                }

        return {
            "symbols": symbol_list,
            "provider": provider,
            "results": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
