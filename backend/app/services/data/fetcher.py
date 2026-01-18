"""
数据获取模块 - 基于OpenBB平台
支持多数据源统一接口: Yahoo Finance, Alpha Vantage, Polygon, FRED等
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from loguru import logger
import time

# OpenBB SDK
from openbb import obb


class OpenBBFetcher:
    """
    OpenBB数据获取器

    OpenBB是一个开源金融数据平台，提供统一的API访问多种数据源。
    文档: https://docs.openbb.co/python/reference
    """

    def __init__(self, provider: str = "yfinance"):
        """
        初始化OpenBB数据获取器

        Args:
            provider: 数据提供商 ('yfinance', 'fmp', 'polygon', 'intrinio', 'tiingo' 等)
        """
        self.provider = provider
        logger.info(f"初始化OpenBB数据获取器: provider={provider}")

    # ==================== 股票价格数据 ====================

    def fetch_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取股票历史价格数据

        Args:
            symbol: 股票代码 (如 'AAPL', 'MSFT')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD), 默认为今天
            interval: 数据频率 ('1m', '5m', '15m', '30m', '1h', '1d', '1W', '1M')

        Returns:
            DataFrame with OHLCV data
        """
        try:
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")
            logger.info(f"获取历史数据: {symbol}, {start_date} ~ {end_date}, interval={interval}")

            # 使用OpenBB获取数据
            output = obb.equity.price.historical(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=self.provider
            )

            df = output.to_dataframe()

            if df.empty:
                logger.warning(f"未获取到数据: {symbol}")
                return pd.DataFrame()

            # 标准化列名
            df = self._standardize_columns(df)

            # 添加额外信息
            df['symbol'] = symbol
            df['pct_change'] = df['close'].pct_change() * 100

            # 确保日期列正确
            if 'date' not in df.columns and df.index.name == 'date':
                df = df.reset_index()

            logger.success(f"成功获取 {len(df)} 条数据: {symbol}")
            return df

        except Exception as e:
            logger.error(f"获取数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票实时报价

        Args:
            symbol: 股票代码

        Returns:
            实时报价字典
        """
        try:
            output = obb.equity.price.quote(
                symbol=symbol,
                provider=self.provider
            )
            df = output.to_dataframe()

            if df.empty:
                return {}

            return df.iloc[0].to_dict()

        except Exception as e:
            logger.error(f"获取报价失败: {symbol}, 错误: {e}")
            return {}

    # ==================== 基本面数据 ====================

    def fetch_profile(self, symbol: str) -> Dict[str, Any]:
        """
        获取公司基本信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息字典
        """
        try:
            output = obb.equity.profile(
                symbol=symbol,
                provider=self.provider
            )
            df = output.to_dataframe()

            if df.empty:
                return {}

            info = df.iloc[0].to_dict()
            return {
                'symbol': symbol,
                'name': info.get('name', info.get('long_name', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('market_cap', 0),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'country': info.get('country', ''),
                'website': info.get('website', ''),
                'description': info.get('description', info.get('long_business_summary', ''))
            }

        except Exception as e:
            logger.error(f"获取公司信息失败: {symbol}, 错误: {e}")
            return {}

    def fetch_income_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5
    ) -> pd.DataFrame:
        """
        获取利润表数据

        Args:
            symbol: 股票代码
            period: 'annual' 或 'quarter'
            limit: 返回记录数量

        Returns:
            利润表DataFrame
        """
        try:
            output = obb.equity.fundamental.income(
                symbol=symbol,
                period=period,
                limit=limit,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取利润表失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_balance_sheet(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5
    ) -> pd.DataFrame:
        """
        获取资产负债表数据

        Args:
            symbol: 股票代码
            period: 'annual' 或 'quarter'
            limit: 返回记录数量

        Returns:
            资产负债表DataFrame
        """
        try:
            output = obb.equity.fundamental.balance(
                symbol=symbol,
                period=period,
                limit=limit,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取资产负债表失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_cash_flow(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5
    ) -> pd.DataFrame:
        """
        获取现金流量表数据

        Args:
            symbol: 股票代码
            period: 'annual' 或 'quarter'
            limit: 返回记录数量

        Returns:
            现金流量表DataFrame
        """
        try:
            output = obb.equity.fundamental.cash(
                symbol=symbol,
                period=period,
                limit=limit,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取现金流量表失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_ratios(self, symbol: str) -> pd.DataFrame:
        """
        获取财务比率

        Args:
            symbol: 股票代码

        Returns:
            财务比率DataFrame
        """
        try:
            output = obb.equity.fundamental.ratios(
                symbol=symbol,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取财务比率失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    # ==================== 市场数据 ====================

    def fetch_index_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取指数历史数据

        Args:
            symbol: 指数代码 (如 '^GSPC' for S&P 500, '^DJI' for Dow Jones)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            指数数据DataFrame
        """
        try:
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")

            output = obb.index.price.historical(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                provider=self.provider
            )

            df = output.to_dataframe()
            df = self._standardize_columns(df)
            df['symbol'] = symbol

            return df

        except Exception as e:
            logger.error(f"获取指数数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_market_indices(self) -> pd.DataFrame:
        """
        获取主要市场指数列表

        Returns:
            指数列表DataFrame
        """
        try:
            output = obb.index.available(provider=self.provider)
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取指数列表失败: {e}")
            return pd.DataFrame()

    # ==================== 新闻与事件 ====================

    def fetch_news(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        获取股票相关新闻

        Args:
            symbols: 股票代码(单个或列表)
            limit: 返回新闻数量

        Returns:
            新闻DataFrame
        """
        try:
            if symbols:
                if isinstance(symbols, list):
                    symbols = ",".join(symbols)
                output = obb.news.company(
                    symbol=symbols,
                    limit=limit,
                    provider=self.provider
                )
            else:
                output = obb.news.world(
                    limit=limit,
                    provider=self.provider
                )

            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
            return pd.DataFrame()

    def fetch_earnings_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取财报日历

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            财报日历DataFrame
        """
        try:
            output = obb.equity.calendar.earnings(
                start_date=start_date,
                end_date=end_date,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取财报日历失败: {e}")
            return pd.DataFrame()

    def fetch_dividend_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分红日历

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            分红日历DataFrame
        """
        try:
            output = obb.equity.calendar.dividend(
                start_date=start_date,
                end_date=end_date,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取分红日历失败: {e}")
            return pd.DataFrame()

    # ==================== 经济数据 ====================

    def fetch_economic_indicator(
        self,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取经济指标数据 (来自FRED)

        Args:
            indicator: 指标代码 (如 'GDP', 'UNRATE', 'CPIAUCSL')
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            经济指标DataFrame
        """
        try:
            output = obb.economy.fred_series(
                symbol=indicator,
                start_date=start_date,
                end_date=end_date
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取经济指标失败: {indicator}, 错误: {e}")
            return pd.DataFrame()

    # ==================== ETF数据 ====================

    def fetch_etf_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取ETF历史数据

        Args:
            symbol: ETF代码 (如 'SPY', 'QQQ')
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            ETF数据DataFrame
        """
        try:
            end_date = end_date or datetime.now().strftime("%Y-%m-%d")

            output = obb.etf.historical(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                provider=self.provider
            )

            df = output.to_dataframe()
            df = self._standardize_columns(df)
            df['symbol'] = symbol

            return df

        except Exception as e:
            logger.error(f"获取ETF数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def fetch_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """
        获取ETF持仓

        Args:
            symbol: ETF代码

        Returns:
            持仓DataFrame
        """
        try:
            output = obb.etf.holdings(
                symbol=symbol,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取ETF持仓失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    # ==================== 期权数据 ====================

    def fetch_options_chains(
        self,
        symbol: str,
        expiration: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取期权链数据

        Args:
            symbol: 标的代码
            expiration: 到期日 (YYYY-MM-DD)

        Returns:
            期权链DataFrame
        """
        try:
            output = obb.derivatives.options.chains(
                symbol=symbol,
                provider=self.provider
            )
            return output.to_dataframe()

        except Exception as e:
            logger.error(f"获取期权链失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    # ==================== 批量操作 ====================

    def fetch_multiple_stocks(
        self,
        symbols: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        delay: float = 0.5
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            delay: 请求间隔时间(秒)

        Returns:
            字典: {symbol: DataFrame}
        """
        results = {}

        for i, symbol in enumerate(symbols, 1):
            logger.info(f"获取进度: {i}/{len(symbols)} - {symbol}")

            df = self.fetch_historical(symbol, start_date, end_date)
            if not df.empty:
                results[symbol] = df

            # 延迟避免API限流
            if i < len(symbols):
                time.sleep(delay)

        logger.success(f"成功获取 {len(results)}/{len(symbols)} 只股票数据")
        return results

    # ==================== 股票筛选 ====================

    def screen_stocks(
        self,
        market_cap_min: Optional[float] = None,
        market_cap_max: Optional[float] = None,
        sector: Optional[str] = None,
        country: str = "US"
    ) -> pd.DataFrame:
        """
        股票筛选

        Args:
            market_cap_min: 最小市值
            market_cap_max: 最大市值
            sector: 行业
            country: 国家

        Returns:
            符合条件的股票列表
        """
        try:
            output = obb.equity.screener(
                country=country,
                provider=self.provider
            )
            df = output.to_dataframe()

            # 筛选条件
            if market_cap_min and 'market_cap' in df.columns:
                df = df[df['market_cap'] >= market_cap_min]
            if market_cap_max and 'market_cap' in df.columns:
                df = df[df['market_cap'] <= market_cap_max]
            if sector and 'sector' in df.columns:
                df = df[df['sector'].str.contains(sector, case=False, na=False)]

            return df

        except Exception as e:
            logger.error(f"股票筛选失败: {e}")
            return pd.DataFrame()

    # ==================== 辅助方法 ====================

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            # 价格列
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume',
            # 其他可能的列名
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'adj_close_price': 'adj_close',
            'trade_volume': 'volume',
            # 日期列
            'Date': 'date',
            'datetime': 'date',
            'timestamp': 'date'
        }

        # 应用列名映射
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        return df

    def get_available_providers(self) -> List[str]:
        """获取可用的数据提供商列表"""
        return [
            "yfinance",      # Yahoo Finance (免费)
            "fmp",           # Financial Modeling Prep
            "polygon",       # Polygon.io
            "intrinio",      # Intrinio
            "tiingo",        # Tiingo
            "alpha_vantage", # Alpha Vantage
            "cboe",          # CBOE
            "tradingview"    # TradingView
        ]


class DataValidator:
    """数据验证类"""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        验证DataFrame数据质量

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 检查必需列
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"缺少必需列: {missing_columns}")

        # 检查数据行数
        if len(df) == 0:
            errors.append("数据为空")
            return False, errors

        # 检查价格逻辑
        if 'high' in df.columns and 'low' in df.columns:
            if (df['high'] < df['low']).any():
                errors.append("存在高价低于低价的异常数据")

        if 'high' in df.columns and 'close' in df.columns:
            if (df['high'] < df['close']).any():
                errors.append("存在高价低于收盘价的异常数据")

        if 'low' in df.columns and 'close' in df.columns:
            if (df['low'] > df['close']).any():
                errors.append("存在低价高于收盘价的异常数据")

        # 检查缺失值
        available_columns = [col for col in required_columns if col in df.columns]
        if available_columns:
            null_counts = df[available_columns].isnull().sum()
            if null_counts.sum() > 0:
                errors.append(f"存在缺失值: {null_counts[null_counts > 0].to_dict()}")

        # 检查重复日期
        if 'date' in df.columns and df['date'].duplicated().any():
            errors.append("存在重复日期")

        is_valid = len(errors) == 0
        return is_valid, errors


# 兼容性别名: 保持与旧代码的兼容
class DataFetcher(OpenBBFetcher):
    """
    数据获取器 (兼容性别名)

    新代码请直接使用 OpenBBFetcher
    """

    def __init__(self, source: str = "yahoo"):
        # 将旧的source参数映射到OpenBB的provider
        provider_mapping = {
            "yahoo": "yfinance",
            "yfinance": "yfinance",
            "fmp": "fmp",
            "polygon": "polygon"
        }
        provider = provider_mapping.get(source, "yfinance")
        super().__init__(provider=provider)

    def fetch_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """兼容旧接口"""
        return self.fetch_historical(symbol, start_date, end_date, interval)

    def fetch_yahoo(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """兼容旧接口"""
        return self.fetch_historical(symbol, start_date, end_date)

    def fetch_tushare(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """兼容旧接口 - Tushare数据暂不支持，返回空"""
        logger.warning("Tushare数据源暂不支持，请使用其他数据源")
        return pd.DataFrame()

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """兼容旧接口"""
        return self.fetch_profile(symbol)


if __name__ == "__main__":
    # 测试代码
    logger.info("测试OpenBB数据获取模块")

    # 初始化获取器
    fetcher = OpenBBFetcher(provider="yfinance")

    # 测试1: 获取历史数据
    print("\n=== 1. 获取AAPL历史数据 ===")
    df = fetcher.fetch_historical(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(df.head())
    print(f"数据形状: {df.shape}")

    # 测试2: 获取实时报价
    print("\n=== 2. 获取实时报价 ===")
    quote = fetcher.fetch_quote("AAPL")
    for k, v in list(quote.items())[:10]:
        print(f"  {k}: {v}")

    # 测试3: 获取公司信息
    print("\n=== 3. 获取公司信息 ===")
    profile = fetcher.fetch_profile("AAPL")
    for k, v in profile.items():
        if v:
            print(f"  {k}: {v}")

    # 测试4: 获取指数数据
    print("\n=== 4. 获取S&P 500指数数据 ===")
    index_df = fetcher.fetch_index_historical(
        symbol="^GSPC",
        start_date="2024-01-01"
    )
    if not index_df.empty:
        print(index_df.tail())

    # 测试5: 批量获取
    print("\n=== 5. 批量获取多只股票 ===")
    symbols = ["AAPL", "MSFT", "GOOGL"]
    results = fetcher.fetch_multiple_stocks(
        symbols=symbols,
        start_date="2024-01-01",
        delay=0.5
    )
    for symbol, data in results.items():
        print(f"  {symbol}: {len(data)} 条数据")

    # 测试6: 数据验证
    print("\n=== 6. 数据验证 ===")
    validator = DataValidator()
    is_valid, errors = validator.validate_dataframe(df)
    print(f"验证结果: {'通过' if is_valid else '失败'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    print("\n✅ 所有测试完成!")
