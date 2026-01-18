"""
数据管理 API - 基于 OpenBB 平台
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from app.core.database import get_session
from app.services.data.fetcher import OpenBBFetcher
from app.services.data.cleaner import DataCleaner
from app.services.features.indicators import TechnicalIndicators


router = APIRouter()


# ==================== 请求/响应模型 ====================

class StockDataRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    provider: str = "yfinance"  # yfinance, fmp, polygon, intrinio
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
    provider: str = "yfinance"


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
    """获取数据源状态 - OpenBB 支持的数据提供商"""
    return [
        {
            "name": "OpenBB Platform",
            "type": "aggregator",
            "status": "connected",
            "last_sync": datetime.now().isoformat(),
            "records": 0,
            "size": "N/A",
            "description": "统一金融数据平台"
        },
        {
            "name": "Yahoo Finance",
            "type": "provider",
            "status": "connected",
            "last_sync": datetime.now().isoformat(),
            "records": 125000,
            "size": "850 MB",
            "provider_key": "yfinance"
        },
        {
            "name": "Financial Modeling Prep",
            "type": "provider",
            "status": "available",
            "last_sync": None,
            "records": 0,
            "size": "0 MB",
            "provider_key": "fmp"
        },
        {
            "name": "Polygon.io",
            "type": "provider",
            "status": "available",
            "last_sync": None,
            "records": 0,
            "size": "0 MB",
            "provider_key": "polygon"
        },
        {
            "name": "FRED (Federal Reserve)",
            "type": "provider",
            "status": "connected",
            "last_sync": datetime.now().isoformat(),
            "records": 50000,
            "size": "120 MB",
            "provider_key": "fred"
        },
        {
            "name": "PostgreSQL",
            "type": "database",
            "status": "connected",
            "last_sync": datetime.now().isoformat(),
            "records": 258000,
            "size": "1.8 GB"
        }
    ]


@router.get("/providers")
async def get_providers():
    """获取可用的数据提供商列表"""
    return {
        "equity": ["yfinance", "fmp", "polygon", "intrinio", "tiingo"],
        "index": ["yfinance", "fmp"],
        "etf": ["yfinance", "fmp"],
        "crypto": ["yfinance", "polygon", "coinbase"],
        "forex": ["yfinance", "polygon", "fmp"],
        "economy": ["fred", "oecd", "econdb"],
        "news": ["benzinga", "fmp", "polygon"]
    }


@router.get("/stocks")
async def get_stocks(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取股票列表"""
    stocks = [
        {"symbol": "AAPL", "name": "苹果公司", "sector": "Technology", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "GOOGL", "name": "谷歌", "sector": "Technology", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "MSFT", "name": "微软", "sector": "Technology", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "NVDA", "name": "英伟达", "sector": "Technology", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "TSLA", "name": "特斯拉", "sector": "Consumer Cyclical", "records": 2520, "last_update": datetime.now(), "status": "outdated"},
        {"symbol": "AMZN", "name": "亚马逊", "sector": "Consumer Cyclical", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "META", "name": "Meta", "sector": "Technology", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "NFLX", "name": "奈飞", "sector": "Communication Services", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "JPM", "name": "摩根大通", "sector": "Financial Services", "records": 2520, "last_update": datetime.now(), "status": "updated"},
        {"symbol": "V", "name": "Visa", "sector": "Financial Services", "records": 2520, "last_update": datetime.now(), "status": "updated"},
    ]

    if search:
        stocks = [s for s in stocks if search.lower() in s["symbol"].lower() or search in s["name"]]

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
    provider: str = "yfinance"
):
    """获取单只股票历史数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(provider)
        df = fetcher.fetch_historical(
            symbol,
            start_date or "2024-01-01",
            end_date or datetime.now().strftime("%Y-%m-%d"),
            interval=interval
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的数据")

        # Replace NaN values with None for JSON serialization
        df = df.fillna(0)  # or use df.where(pd.notnull(df), None) for None values
        data = df.reset_index().to_dict(orient="records")

        # 处理日期序列化
        for record in data:
            for key, value in record.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = value.isoformat()
                # Handle any remaining float NaN/Inf
                elif isinstance(value, float) and (pd.isna(value) or np.isinf(value)):
                    record[key] = 0

        return {
            "symbol": symbol,
            "provider": provider,
            "interval": interval,
            "records": len(data),
            "data": data[-100:]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    provider: str = "yfinance"
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
    """同步股票数据 (OpenBB)"""
    try:
        fetcher = get_fetcher(request.provider)
        cleaner = DataCleaner()
        results = []

        for symbol in request.symbols:
            try:
                df = fetcher.fetch_historical(
                    symbol,
                    request.start_date,
                    request.end_date
                )

                df = cleaner.clean(df)

                results.append({
                    "symbol": symbol,
                    "status": "success",
                    "records": len(df),
                    "provider": request.provider
                })
            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "status": "failed",
                    "error": str(e)
                })

        return {
            "status": "completed",
            "provider": request.provider,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/{symbol}")
async def get_index_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "yfinance"
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
    provider: str = "yfinance"
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
    provider: str = "yfinance"
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
    """获取数据质量指标"""
    return {
        "completeness": 98.5,
        "accuracy": 99.2,
        "consistency": 97.8,
        "timeliness": 92.3,
        "overall": 96.9,
        "provider_status": {
            "yfinance": "healthy",
            "fmp": "available",
            "fred": "healthy",
            "polygon": "available"
        }
    }


@router.get("/storage")
async def get_storage_stats():
    """获取存储统计"""
    return {
        "total_size_gb": 5.9,
        "max_size_gb": 10.0,
        "items": [
            {"name": "价格数据", "size_gb": 2.5, "color": "#00f5ff"},
            {"name": "特征数据", "size_gb": 1.8, "color": "#bf00ff"},
            {"name": "模型文件", "size_gb": 0.8, "color": "#00ff88"},
            {"name": "回测结果", "size_gb": 0.5, "color": "#ffa502"},
            {"name": "日志文件", "size_gb": 0.3, "color": "#ff6348"}
        ]
    }


@router.get("/features/{symbol}")
async def get_features(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: str = "yfinance"
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
    provider: str = "yfinance"
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
