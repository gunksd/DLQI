"""
统计特征计算模块
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from loguru import logger
from scipy import stats


class StatisticalFeatures:
    """统计特征计算类 - 30+特征"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化

        Args:
            df: 包含价格数据的DataFrame
        """
        self.df = df.copy()

    def calculate_all(self) -> pd.DataFrame:
        """计算所有统计特征"""
        logger.info("开始计算统计特征...")

        self.add_return_features()
        self.add_volatility_features()
        self.add_distribution_features()
        self.add_risk_metrics()
        self.add_trend_features()
        self.add_autocorrelation_features()

        logger.success(f"统计特征计算完成, 共 {len(self.df.columns)} 列")
        return self.df

    def add_return_features(
        self,
        windows: List[int] = [1, 5, 10, 20, 60]
    ) -> pd.DataFrame:
        """
        添加收益率特征

        Args:
            windows: 滚动窗口列表
        """
        # 简单收益率
        self.df['return_1d'] = self.df['close'].pct_change()

        # 对数收益率
        self.df['log_return_1d'] = np.log(self.df['close'] / self.df['close'].shift(1))

        # 多周期收益率
        for w in windows:
            self.df[f'return_{w}d'] = self.df['close'].pct_change(periods=w)
            self.df[f'log_return_{w}d'] = np.log(
                self.df['close'] / self.df['close'].shift(w)
            )

        # 滚动累计收益
        for w in windows:
            self.df[f'cumulative_return_{w}d'] = (
                1 + self.df['return_1d']
            ).rolling(window=w).apply(lambda x: x.prod() - 1, raw=True)

        # 收益率均值
        for w in [20, 60]:
            self.df[f'return_mean_{w}d'] = self.df['return_1d'].rolling(window=w).mean()

        # 超额收益 (相对于均值)
        self.df['excess_return'] = self.df['return_1d'] - self.df['return_mean_20d']

        logger.info(f"收益率特征添加完成: windows={windows}")
        return self.df

    def add_volatility_features(
        self,
        windows: List[int] = [5, 10, 20, 60]
    ) -> pd.DataFrame:
        """
        添加波动率特征

        Args:
            windows: 滚动窗口列表
        """
        # 历史波动率 (标准差)
        for w in windows:
            self.df[f'volatility_{w}d'] = self.df['return_1d'].rolling(window=w).std()

            # 年化波动率
            self.df[f'volatility_annual_{w}d'] = self.df[f'volatility_{w}d'] * np.sqrt(252)

        # 波动率变化
        self.df['volatility_change'] = (
            self.df['volatility_20d'] / self.df['volatility_20d'].shift(20) - 1
        )

        # Parkinson波动率 (使用高低价)
        for w in windows:
            hl_ratio = np.log(self.df['high'] / self.df['low'])
            self.df[f'parkinson_vol_{w}d'] = np.sqrt(
                (1 / (4 * np.log(2))) * (hl_ratio ** 2).rolling(window=w).mean()
            )

        # Garman-Klass波动率
        for w in [20]:
            hl = np.log(self.df['high'] / self.df['low']) ** 2
            co = np.log(self.df['close'] / self.df['open']) ** 2
            gk = 0.5 * hl - (2 * np.log(2) - 1) * co
            self.df[f'gk_vol_{w}d'] = np.sqrt(gk.rolling(window=w).mean())

        # 波动率比率
        self.df['volatility_ratio_5_20'] = self.df['volatility_5d'] / (
            self.df['volatility_20d'] + 1e-10
        )

        logger.info(f"波动率特征添加完成: windows={windows}")
        return self.df

    def add_distribution_features(
        self,
        windows: List[int] = [20, 60]
    ) -> pd.DataFrame:
        """
        添加分布特征 (偏度, 峰度)

        Args:
            windows: 滚动窗口列表
        """
        for w in windows:
            # 偏度 (收益分布的不对称性)
            self.df[f'skewness_{w}d'] = self.df['return_1d'].rolling(window=w).skew()

            # 峰度 (收益分布的尾部厚度)
            self.df[f'kurtosis_{w}d'] = self.df['return_1d'].rolling(window=w).kurt()

            # 分位数特征
            self.df[f'return_quantile25_{w}d'] = self.df['return_1d'].rolling(window=w).quantile(0.25)
            self.df[f'return_quantile75_{w}d'] = self.df['return_1d'].rolling(window=w).quantile(0.75)

            # 四分位距
            self.df[f'return_iqr_{w}d'] = (
                self.df[f'return_quantile75_{w}d'] - self.df[f'return_quantile25_{w}d']
            )

        # 正负收益比例
        for w in windows:
            self.df[f'positive_return_ratio_{w}d'] = (
                (self.df['return_1d'] > 0).rolling(window=w).mean()
            )

        logger.info(f"分布特征添加完成: windows={windows}")
        return self.df

    def add_risk_metrics(
        self,
        windows: List[int] = [20, 60, 252]
    ) -> pd.DataFrame:
        """
        添加风险指标

        Args:
            windows: 滚动窗口列表
        """
        for w in windows:
            # 夏普比率 (简化版,假设无风险利率为0)
            mean_return = self.df['return_1d'].rolling(window=w).mean()
            std_return = self.df['return_1d'].rolling(window=w).std()
            self.df[f'sharpe_{w}d'] = (mean_return / (std_return + 1e-10)) * np.sqrt(252)

            # 索提诺比率 (只考虑下行风险)
            downside_return = self.df['return_1d'].copy()
            downside_return[downside_return > 0] = 0
            downside_std = downside_return.rolling(window=w).std()
            self.df[f'sortino_{w}d'] = (mean_return / (downside_std + 1e-10)) * np.sqrt(252)

            # 最大回撤
            rolling_max = self.df['close'].rolling(window=w, min_periods=1).max()
            drawdown = (self.df['close'] - rolling_max) / rolling_max
            self.df[f'max_drawdown_{w}d'] = drawdown.rolling(window=w).min()

            # VaR (历史模拟法, 95%置信度)
            self.df[f'var_95_{w}d'] = self.df['return_1d'].rolling(window=w).quantile(0.05)

            # CVaR / Expected Shortfall
            def calculate_cvar(returns):
                var = np.percentile(returns.dropna(), 5)
                return returns[returns <= var].mean()

            self.df[f'cvar_95_{w}d'] = self.df['return_1d'].rolling(window=w).apply(
                calculate_cvar, raw=False
            )

        # 卡尔马比率
        annual_return = self.df['return_1d'].rolling(window=252).mean() * 252
        max_dd = self.df['max_drawdown_252d'].abs()
        self.df['calmar_ratio'] = annual_return / (max_dd + 1e-10)

        logger.info(f"风险指标添加完成: windows={windows}")
        return self.df

    def add_trend_features(
        self,
        windows: List[int] = [5, 10, 20, 60]
    ) -> pd.DataFrame:
        """
        添加趋势特征

        Args:
            windows: 滚动窗口列表
        """
        for w in windows:
            # 价格相对位置 (相对于N日最高/最低)
            rolling_max = self.df['close'].rolling(window=w).max()
            rolling_min = self.df['close'].rolling(window=w).min()
            self.df[f'price_position_{w}d'] = (self.df['close'] - rolling_min) / (
                rolling_max - rolling_min + 1e-10
            )

            # 价格与均线的距离
            sma = self.df['close'].rolling(window=w).mean()
            self.df[f'price_to_sma_{w}d'] = (self.df['close'] - sma) / sma

            # 线性回归斜率
            def calculate_slope(series):
                x = np.arange(len(series))
                slope, _, _, _, _ = stats.linregress(x, series)
                return slope

            self.df[f'trend_slope_{w}d'] = self.df['close'].rolling(window=w).apply(
                calculate_slope, raw=True
            )

        # 趋势强度 (ADX的简化版)
        plus_dm = self.df['high'].diff()
        minus_dm = -self.df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            self.df['high'] - self.df['low'],
            np.abs(self.df['high'] - self.df['close'].shift()),
            np.abs(self.df['low'] - self.df['close'].shift())
        ], axis=1).max(axis=1)

        atr_14 = tr.rolling(window=14).mean()
        plus_di = 100 * plus_dm.rolling(window=14).mean() / (atr_14 + 1e-10)
        minus_di = 100 * minus_dm.rolling(window=14).mean() / (atr_14 + 1e-10)

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        self.df['adx'] = dx.rolling(window=14).mean()

        logger.info(f"趋势特征添加完成: windows={windows}")
        return self.df

    def add_autocorrelation_features(
        self,
        lags: List[int] = [1, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        添加自相关特征

        Args:
            lags: 滞后期列表
        """
        for lag in lags:
            # 收益率自相关
            self.df[f'return_autocorr_lag{lag}'] = self.df['return_1d'].rolling(
                window=60
            ).apply(lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan, raw=False)

            # 滞后收益率
            self.df[f'return_lag{lag}'] = self.df['return_1d'].shift(lag)

        # 收益率与成交量的相关性
        if 'volume' in self.df.columns:
            self.df['return_volume_corr'] = self.df['return_1d'].rolling(window=20).corr(
                self.df['volume']
            )

        logger.info(f"自相关特征添加完成: lags={lags}")
        return self.df


if __name__ == "__main__":
    # 测试代码
    logger.info("测试统计特征模块")

    # 创建测试数据
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2022-01-01', periods=n)

    close = 100 + np.random.randn(n).cumsum()
    test_data = pd.DataFrame({
        'date': dates,
        'open': close + np.random.randn(n) * 0.5,
        'high': close + np.abs(np.random.randn(n)),
        'low': close - np.abs(np.random.randn(n)),
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n)
    })

    # 计算统计特征
    sf = StatisticalFeatures(test_data)
    df_with_stats = sf.calculate_all()

    print(f"\n=== 统计特征统计 ===")
    print(f"原始列数: 6")
    print(f"特征列数: {len(df_with_stats.columns)}")

    print(f"\n=== 关键指标预览 ===")
    key_cols = ['close', 'return_1d', 'volatility_20d', 'sharpe_252d',
                'max_drawdown_252d', 'skewness_60d']
    print(df_with_stats[key_cols].tail(10))
