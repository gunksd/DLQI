"""
策略生成模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from loguru import logger


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, params: Optional[Dict] = None):
        """
        初始化策略

        Args:
            name: 策略名称
            params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.signals: List[int] = []

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, index: int) -> int:
        """
        生成交易信号

        Args:
            data: 行情数据
            index: 当前索引

        Returns:
            信号: 1=买入, -1=卖出, 0=持有
        """
        pass

    def run(self, data: pd.DataFrame) -> pd.Series:
        """
        运行策略生成所有信号

        Args:
            data: 行情数据

        Returns:
            信号序列
        """
        self.signals = []
        for i in range(len(data)):
            signal = self.generate_signal(data, i)
            self.signals.append(signal)

        return pd.Series(self.signals, index=data.index)


class MLStrategy(BaseStrategy):
    """基于机器学习的策略"""

    def __init__(
        self,
        name: str = "ml_strategy",
        model=None,
        threshold: float = 0.02,
        params: Optional[Dict] = None
    ):
        """
        初始化

        Args:
            name: 策略名称
            model: 机器学习模型
            threshold: 信号阈值
            params: 其他参数
        """
        super().__init__(name, params)
        self.model = model
        self.threshold = threshold
        self.predictions: Optional[np.ndarray] = None

    def set_predictions(self, predictions: np.ndarray):
        """设置预测结果"""
        self.predictions = predictions

    def generate_signal(self, data: pd.DataFrame, index: int) -> int:
        """生成信号"""
        if self.predictions is None or index >= len(self.predictions):
            return 0

        pred = self.predictions[index]

        if np.isnan(pred):
            return 0

        if pred > self.threshold:
            return 1  # 买入
        elif pred < -self.threshold:
            return -1  # 卖出
        return 0


class TechnicalStrategy(BaseStrategy):
    """技术指标策略"""

    def __init__(
        self,
        name: str = "technical_strategy",
        params: Optional[Dict] = None
    ):
        default_params = {
            'ma_short': 5,
            'ma_long': 20,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'use_macd': True,
            'use_rsi': True,
            'use_bb': True
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signal(self, data: pd.DataFrame, index: int) -> int:
        """生成信号"""
        signals = []

        # 均线交叉
        if index >= self.params['ma_long']:
            ma_short = data['close'].iloc[index-self.params['ma_short']:index].mean()
            ma_long = data['close'].iloc[index-self.params['ma_long']:index].mean()

            if ma_short > ma_long:
                signals.append(1)
            elif ma_short < ma_long:
                signals.append(-1)
            else:
                signals.append(0)

        # RSI
        if self.params['use_rsi'] and 'rsi_14' in data.columns:
            rsi = data['rsi_14'].iloc[index]
            if not np.isnan(rsi):
                if rsi < self.params['rsi_oversold']:
                    signals.append(1)
                elif rsi > self.params['rsi_overbought']:
                    signals.append(-1)
                else:
                    signals.append(0)

        # MACD
        if self.params['use_macd'] and 'macd_cross' in data.columns:
            macd_cross = data['macd_cross'].iloc[index]
            signals.append(int(macd_cross))

        # 布林带
        if self.params['use_bb'] and 'bb_signal' in data.columns:
            bb_signal = data['bb_signal'].iloc[index]
            signals.append(int(bb_signal))

        # 综合信号 (投票机制)
        if not signals:
            return 0

        avg_signal = np.mean(signals)
        if avg_signal > 0.3:
            return 1
        elif avg_signal < -0.3:
            return -1
        return 0


class MomentumStrategy(BaseStrategy):
    """动量策略"""

    def __init__(
        self,
        name: str = "momentum_strategy",
        lookback: int = 20,
        threshold: float = 0.05,
        params: Optional[Dict] = None
    ):
        super().__init__(name, params)
        self.lookback = lookback
        self.threshold = threshold

    def generate_signal(self, data: pd.DataFrame, index: int) -> int:
        """生成信号"""
        if index < self.lookback:
            return 0

        # 计算动量
        current_price = data['close'].iloc[index]
        past_price = data['close'].iloc[index - self.lookback]
        momentum = (current_price - past_price) / past_price

        if momentum > self.threshold:
            return 1
        elif momentum < -self.threshold:
            return -1
        return 0


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""

    def __init__(
        self,
        name: str = "mean_reversion_strategy",
        lookback: int = 20,
        std_threshold: float = 2.0,
        params: Optional[Dict] = None
    ):
        super().__init__(name, params)
        self.lookback = lookback
        self.std_threshold = std_threshold

    def generate_signal(self, data: pd.DataFrame, index: int) -> int:
        """生成信号"""
        if index < self.lookback:
            return 0

        # 计算Z-score
        window = data['close'].iloc[index-self.lookback:index]
        mean = window.mean()
        std = window.std()

        if std == 0:
            return 0

        current_price = data['close'].iloc[index]
        z_score = (current_price - mean) / std

        # 价格偏离均值过多时反向交易
        if z_score > self.std_threshold:
            return -1  # 价格过高,卖出
        elif z_score < -self.std_threshold:
            return 1  # 价格过低,买入
        return 0


class PositionManager:
    """仓位管理"""

    def __init__(
        self,
        method: str = "fixed",
        params: Optional[Dict] = None
    ):
        """
        初始化仓位管理器

        Args:
            method: 仓位计算方法
                - 'fixed': 固定仓位比例
                - 'kelly': Kelly公式
                - 'volatility': 波动率目标
                - 'risk_parity': 风险平价
            params: 参数
        """
        self.method = method
        self.params = params or {}

    def calculate_position(
        self,
        portfolio_value: float,
        price: float,
        signal: int,
        **kwargs
    ) -> int:
        """
        计算仓位大小

        Args:
            portfolio_value: 组合价值
            price: 当前价格
            signal: 交易信号
            **kwargs: 额外参数 (如volatility, win_rate等)

        Returns:
            交易数量
        """
        if signal == 0:
            return 0

        if self.method == "fixed":
            return self._fixed_position(portfolio_value, price)
        elif self.method == "kelly":
            return self._kelly_position(portfolio_value, price, **kwargs)
        elif self.method == "volatility":
            return self._volatility_position(portfolio_value, price, **kwargs)
        else:
            return self._fixed_position(portfolio_value, price)

    def _fixed_position(self, portfolio_value: float, price: float) -> int:
        """固定仓位"""
        fraction = self.params.get('fraction', 0.3)  # 默认30%仓位
        position_value = portfolio_value * fraction
        quantity = int(position_value / price / 100) * 100  # 整百股
        return quantity

    def _kelly_position(
        self,
        portfolio_value: float,
        price: float,
        win_rate: float = 0.55,
        win_loss_ratio: float = 1.5,
        **kwargs
    ) -> int:
        """
        Kelly公式计算最优仓位

        f* = (p * b - q) / b
        其中 p=胜率, q=1-p, b=盈亏比
        """
        q = 1 - win_rate
        kelly_fraction = (win_rate * win_loss_ratio - q) / win_loss_ratio

        # 使用半Kelly降低风险
        kelly_fraction = max(0, min(kelly_fraction * 0.5, 0.25))

        position_value = portfolio_value * kelly_fraction
        quantity = int(position_value / price / 100) * 100
        return quantity

    def _volatility_position(
        self,
        portfolio_value: float,
        price: float,
        volatility: float = 0.02,
        target_volatility: float = 0.15,
        **kwargs
    ) -> int:
        """
        波动率目标仓位

        position = target_vol / asset_vol * base_position
        """
        if volatility <= 0:
            volatility = 0.02  # 默认2%日波动

        # 计算仓位系数
        vol_ratio = target_volatility / (volatility * np.sqrt(252))
        vol_ratio = max(0.1, min(vol_ratio, 2.0))  # 限制范围

        base_fraction = self.params.get('base_fraction', 0.2)
        position_fraction = base_fraction * vol_ratio

        position_value = portfolio_value * position_fraction
        quantity = int(position_value / price / 100) * 100
        return quantity


class SignalCombiner:
    """信号组合器"""

    def __init__(self, method: str = "voting"):
        """
        初始化

        Args:
            method: 组合方法
                - 'voting': 多数投票
                - 'weighted': 加权平均
                - 'unanimous': 全部一致
        """
        self.method = method
        self.strategies: List[BaseStrategy] = []
        self.weights: List[float] = []

    def add_strategy(self, strategy: BaseStrategy, weight: float = 1.0):
        """添加策略"""
        self.strategies.append(strategy)
        self.weights.append(weight)

    def combine_signals(self, data: pd.DataFrame, index: int) -> int:
        """
        组合多个策略的信号

        Args:
            data: 行情数据
            index: 当前索引

        Returns:
            组合信号
        """
        signals = []
        for strategy in self.strategies:
            sig = strategy.generate_signal(data, index)
            signals.append(sig)

        if not signals:
            return 0

        if self.method == "voting":
            # 多数投票
            vote = sum(signals)
            if vote > 0:
                return 1
            elif vote < 0:
                return -1
            return 0

        elif self.method == "weighted":
            # 加权平均
            weighted_sum = sum(s * w for s, w in zip(signals, self.weights))
            total_weight = sum(self.weights)
            avg = weighted_sum / total_weight if total_weight > 0 else 0

            if avg > 0.3:
                return 1
            elif avg < -0.3:
                return -1
            return 0

        elif self.method == "unanimous":
            # 全部一致
            if all(s == 1 for s in signals):
                return 1
            elif all(s == -1 for s in signals):
                return -1
            return 0

        return 0


if __name__ == "__main__":
    # 测试代码
    logger.info("测试策略模块")

    # 创建模拟数据
    np.random.seed(42)
    n = 200
    dates = pd.date_range('2024-01-01', periods=n)

    price = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))

    data = pd.DataFrame({
        'date': dates,
        'close': price,
        'rsi_14': 30 + 40 * np.random.rand(n),
        'macd_cross': np.random.choice([-1, 0, 1], n),
        'bb_signal': np.random.choice([-1, 0, 1], n)
    })

    # 测试技术策略
    print("\n=== 技术策略 ===")
    tech_strategy = TechnicalStrategy()
    tech_signals = tech_strategy.run(data)
    print(f"信号分布: {tech_signals.value_counts().to_dict()}")

    # 测试动量策略
    print("\n=== 动量策略 ===")
    momentum_strategy = MomentumStrategy(lookback=10, threshold=0.03)
    momentum_signals = momentum_strategy.run(data)
    print(f"信号分布: {momentum_signals.value_counts().to_dict()}")

    # 测试仓位管理
    print("\n=== 仓位管理 ===")
    pm = PositionManager(method='kelly')
    qty = pm.calculate_position(
        portfolio_value=1_000_000,
        price=100,
        signal=1,
        win_rate=0.55,
        win_loss_ratio=1.5
    )
    print(f"Kelly仓位: {qty}股")

    # 测试信号组合
    print("\n=== 信号组合 ===")
    combiner = SignalCombiner(method='voting')
    combiner.add_strategy(tech_strategy)
    combiner.add_strategy(momentum_strategy)

    combined_signal = combiner.combine_signals(data, 50)
    print(f"组合信号: {combined_signal}")
