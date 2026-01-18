"""
技术指标计算模块
"""
import pandas as pd
import numpy as np
from typing import Optional, List, Union
from loguru import logger


class TechnicalIndicators:
    """技术指标计算类 - 60+指标"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化

        Args:
            df: 包含OHLCV数据的DataFrame
        """
        self.df = df.copy()
        self._validate_columns()

    def _validate_columns(self):
        """验证必需的列"""
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"缺少必需列: {missing}")

    def calculate_all(self) -> pd.DataFrame:
        """计算所有技术指标"""
        logger.info("开始计算技术指标...")

        # 趋势指标
        self.add_moving_averages()
        self.add_macd()

        # 动量指标
        self.add_rsi()
        self.add_stochastic()
        self.add_williams_r()
        self.add_roc()
        self.add_momentum()

        # 波动率指标
        self.add_bollinger_bands()
        self.add_atr()
        self.add_keltner_channel()

        # 成交量指标
        self.add_volume_indicators()

        # 其他指标
        self.add_pivot_points()

        logger.success(f"技术指标计算完成, 共 {len(self.df.columns)} 列")
        return self.df

    # ==================== 趋势指标 ====================

    def add_moving_averages(
        self,
        periods: List[int] = [5, 10, 20, 60, 120, 250]
    ) -> pd.DataFrame:
        """
        添加移动平均线

        Args:
            periods: MA周期列表
        """
        for period in periods:
            # 简单移动平均
            self.df[f'sma_{period}'] = self.df['close'].rolling(window=period).mean()

            # 指数移动平均
            self.df[f'ema_{period}'] = self.df['close'].ewm(span=period, adjust=False).mean()

            # 加权移动平均
            weights = np.arange(1, period + 1)
            self.df[f'wma_{period}'] = self.df['close'].rolling(window=period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )

        # MA交叉信号
        if 5 in periods and 20 in periods:
            self.df['ma_cross_5_20'] = np.where(
                self.df['sma_5'] > self.df['sma_20'], 1,
                np.where(self.df['sma_5'] < self.df['sma_20'], -1, 0)
            )

        logger.info(f"移动平均线添加完成: {periods}")
        return self.df

    def add_macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """
        添加MACD指标

        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        ema_fast = self.df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df['close'].ewm(span=slow, adjust=False).mean()

        self.df['macd'] = ema_fast - ema_slow
        self.df['macd_signal'] = self.df['macd'].ewm(span=signal, adjust=False).mean()
        self.df['macd_histogram'] = self.df['macd'] - self.df['macd_signal']

        # MACD交叉信号
        self.df['macd_cross'] = np.where(
            self.df['macd'] > self.df['macd_signal'], 1,
            np.where(self.df['macd'] < self.df['macd_signal'], -1, 0)
        )

        logger.info(f"MACD添加完成: fast={fast}, slow={slow}, signal={signal}")
        return self.df

    # ==================== 动量指标 ====================

    def add_rsi(self, periods: List[int] = [6, 12, 14, 24]) -> pd.DataFrame:
        """
        添加RSI指标

        Args:
            periods: RSI周期列表
        """
        for period in periods:
            delta = self.df['close'].diff()

            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)

            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            rs = avg_gain / avg_loss
            self.df[f'rsi_{period}'] = 100 - (100 / (1 + rs))

        # RSI超买超卖信号
        if 14 in periods:
            self.df['rsi_signal'] = np.where(
                self.df['rsi_14'] > 70, -1,  # 超买
                np.where(self.df['rsi_14'] < 30, 1, 0)  # 超卖
            )

        logger.info(f"RSI添加完成: {periods}")
        return self.df

    def add_stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3,
        smooth_k: int = 3
    ) -> pd.DataFrame:
        """
        添加随机指标 (KDJ)

        Args:
            k_period: K值周期
            d_period: D值周期
            smooth_k: K值平滑周期
        """
        # 计算原始K值
        lowest_low = self.df['low'].rolling(window=k_period).min()
        highest_high = self.df['high'].rolling(window=k_period).max()

        raw_k = 100 * (self.df['close'] - lowest_low) / (highest_high - lowest_low + 1e-10)

        # 平滑K值
        self.df['stoch_k'] = raw_k.rolling(window=smooth_k).mean()

        # D值
        self.df['stoch_d'] = self.df['stoch_k'].rolling(window=d_period).mean()

        # J值 (中国市场常用)
        self.df['stoch_j'] = 3 * self.df['stoch_k'] - 2 * self.df['stoch_d']

        # KD交叉信号
        self.df['stoch_cross'] = np.where(
            self.df['stoch_k'] > self.df['stoch_d'], 1,
            np.where(self.df['stoch_k'] < self.df['stoch_d'], -1, 0)
        )

        logger.info(f"随机指标添加完成: K={k_period}, D={d_period}")
        return self.df

    def add_williams_r(self, period: int = 14) -> pd.DataFrame:
        """添加威廉指标"""
        highest_high = self.df['high'].rolling(window=period).max()
        lowest_low = self.df['low'].rolling(window=period).min()

        self.df[f'williams_r_{period}'] = -100 * (highest_high - self.df['close']) / (
            highest_high - lowest_low + 1e-10
        )

        logger.info(f"威廉指标添加完成: {period}")
        return self.df

    def add_roc(self, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """添加变化率指标"""
        for period in periods:
            self.df[f'roc_{period}'] = (
                (self.df['close'] - self.df['close'].shift(period)) /
                self.df['close'].shift(period) * 100
            )

        logger.info(f"ROC添加完成: {periods}")
        return self.df

    def add_momentum(self, periods: List[int] = [10, 20]) -> pd.DataFrame:
        """添加动量指标"""
        for period in periods:
            self.df[f'momentum_{period}'] = self.df['close'] - self.df['close'].shift(period)

        logger.info(f"动量指标添加完成: {periods}")
        return self.df

    # ==================== 波动率指标 ====================

    def add_bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ) -> pd.DataFrame:
        """
        添加布林带

        Args:
            period: 周期
            std_dev: 标准差倍数
        """
        sma = self.df['close'].rolling(window=period).mean()
        std = self.df['close'].rolling(window=period).std()

        self.df['bb_middle'] = sma
        self.df['bb_upper'] = sma + std_dev * std
        self.df['bb_lower'] = sma - std_dev * std
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / sma * 100

        # 价格位置 (0=下轨, 1=上轨)
        self.df['bb_position'] = (self.df['close'] - self.df['bb_lower']) / (
            self.df['bb_upper'] - self.df['bb_lower'] + 1e-10
        )

        # 布林带信号
        self.df['bb_signal'] = np.where(
            self.df['close'] > self.df['bb_upper'], -1,  # 超买
            np.where(self.df['close'] < self.df['bb_lower'], 1, 0)  # 超卖
        )

        logger.info(f"布林带添加完成: period={period}, std={std_dev}")
        return self.df

    def add_atr(self, periods: List[int] = [14, 20]) -> pd.DataFrame:
        """
        添加平均真实波动范围

        Args:
            periods: ATR周期列表
        """
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['tr'] = tr

        for period in periods:
            self.df[f'atr_{period}'] = tr.rolling(window=period).mean()

            # ATR百分比
            self.df[f'atr_pct_{period}'] = self.df[f'atr_{period}'] / self.df['close'] * 100

        logger.info(f"ATR添加完成: {periods}")
        return self.df

    def add_keltner_channel(
        self,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0
    ) -> pd.DataFrame:
        """添加肯特纳通道"""
        ema = self.df['close'].ewm(span=ema_period, adjust=False).mean()

        if f'atr_{atr_period}' not in self.df.columns:
            self.add_atr([atr_period])

        atr = self.df[f'atr_{atr_period}']

        self.df['kc_middle'] = ema
        self.df['kc_upper'] = ema + multiplier * atr
        self.df['kc_lower'] = ema - multiplier * atr

        logger.info(f"肯特纳通道添加完成")
        return self.df

    # ==================== 成交量指标 ====================

    def add_volume_indicators(self) -> pd.DataFrame:
        """添加成交量相关指标"""
        # 成交量移动平均
        for period in [5, 10, 20]:
            self.df[f'volume_sma_{period}'] = self.df['volume'].rolling(window=period).mean()

        # 成交量比率
        self.df['volume_ratio'] = self.df['volume'] / self.df['volume'].rolling(window=20).mean()

        # OBV (能量潮)
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        self.df['obv'] = obv

        # 成交量加权平均价格 (VWAP)
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        self.df['vwap'] = (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()

        # 资金流量指数 (MFI)
        period = 14
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        money_flow = typical_price * self.df['volume']

        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()

        mfi = 100 - (100 / (1 + positive_sum / (negative_sum + 1e-10)))
        self.df['mfi'] = mfi

        # Chaikin资金流
        clv = ((self.df['close'] - self.df['low']) - (self.df['high'] - self.df['close'])) / (
            self.df['high'] - self.df['low'] + 1e-10
        )
        self.df['cmf'] = (clv * self.df['volume']).rolling(window=20).sum() / (
            self.df['volume'].rolling(window=20).sum() + 1e-10
        )

        logger.info("成交量指标添加完成")
        return self.df

    # ==================== 其他指标 ====================

    def add_pivot_points(self) -> pd.DataFrame:
        """添加轴心点"""
        pivot = (self.df['high'].shift(1) + self.df['low'].shift(1) + self.df['close'].shift(1)) / 3

        self.df['pivot'] = pivot
        self.df['r1'] = 2 * pivot - self.df['low'].shift(1)
        self.df['s1'] = 2 * pivot - self.df['high'].shift(1)
        self.df['r2'] = pivot + (self.df['high'].shift(1) - self.df['low'].shift(1))
        self.df['s2'] = pivot - (self.df['high'].shift(1) - self.df['low'].shift(1))

        logger.info("轴心点添加完成")
        return self.df

    def add_price_patterns(self) -> pd.DataFrame:
        """添加价格形态特征"""
        # 涨跌标记
        self.df['is_up'] = (self.df['close'] > self.df['open']).astype(int)

        # 实体大小
        self.df['body_size'] = np.abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = self.df['body_size'] / self.df['open'] * 100

        # 上下影线
        self.df['upper_shadow'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_shadow'] = self.df[['open', 'close']].min(axis=1) - self.df['low']

        # 振幅
        self.df['amplitude'] = (self.df['high'] - self.df['low']) / self.df['low'] * 100

        # 连涨连跌天数
        self.df['consecutive_up'] = self._count_consecutive(self.df['is_up'])
        self.df['consecutive_down'] = self._count_consecutive(1 - self.df['is_up'])

        logger.info("价格形态特征添加完成")
        return self.df

    def _count_consecutive(self, series: pd.Series) -> pd.Series:
        """计算连续计数"""
        result = []
        count = 0
        for val in series:
            if val == 1:
                count += 1
            else:
                count = 0
            result.append(count)
        return pd.Series(result, index=series.index)


if __name__ == "__main__":
    # 测试代码
    logger.info("测试技术指标模块")

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

    # 计算技术指标
    ti = TechnicalIndicators(test_data)
    df_with_indicators = ti.calculate_all()

    print(f"\n=== 技术指标统计 ===")
    print(f"原始列数: 6")
    print(f"指标列数: {len(df_with_indicators.columns)}")
    print(f"\n所有列名:")
    for col in sorted(df_with_indicators.columns):
        print(f"  - {col}")

    print(f"\n=== 数据预览 ===")
    print(df_with_indicators[['close', 'sma_20', 'rsi_14', 'macd', 'bb_upper', 'bb_lower']].tail(10))
