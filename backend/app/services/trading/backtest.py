"""
回测引擎
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from enum import Enum


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Order:
    """订单"""
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    order_type: OrderType = OrderType.MARKET
    timestamp: datetime = None
    order_id: str = ""

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if not self.order_id:
            self.order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class Trade:
    """成交记录"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    amount: float
    commission: float
    slippage: float
    timestamp: datetime
    trade_id: str = ""

    def __post_init__(self):
        if not self.trade_id:
            self.trade_id = f"TRD_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    def update(self, trade: Trade, current_price: float):
        """更新持仓"""
        if trade.side == OrderSide.BUY:
            # 买入
            total_cost = self.quantity * self.avg_price + trade.quantity * trade.price
            self.quantity += trade.quantity
            self.avg_price = total_cost / self.quantity if self.quantity > 0 else 0
        else:
            # 卖出
            self.realized_pnl += (trade.price - self.avg_price) * trade.quantity
            self.quantity -= trade.quantity

        self.market_value = self.quantity * current_price
        self.unrealized_pnl = (current_price - self.avg_price) * self.quantity


@dataclass
class Portfolio:
    """投资组合"""
    cash: float
    initial_capital: float
    positions: Dict[str, Position] = field(default_factory=dict)
    total_commission: float = 0.0
    total_slippage: float = 0.0

    @property
    def market_value(self) -> float:
        """持仓市值"""
        return sum(pos.market_value for pos in self.positions.values())

    @property
    def total_value(self) -> float:
        """总资产"""
        return self.cash + self.market_value

    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_value - self.initial_capital

    @property
    def total_return(self) -> float:
        """总收益率"""
        return self.total_pnl / self.initial_capital

    def get_position(self, symbol: str) -> Position:
        """获取持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        commission_rate: float = 0.0003,  # 万三
        slippage_rate: float = 0.001,     # 千分之一
        min_commission: float = 5.0       # 最低佣金
    ):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission_rate: 佣金率
            slippage_rate: 滑点率
            min_commission: 最低佣金
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.min_commission = min_commission

        self.portfolio = None
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        self.daily_values: List[Dict] = []
        self.current_date = None

    def reset(self):
        """重置回测状态"""
        self.portfolio = Portfolio(
            cash=self.initial_capital,
            initial_capital=self.initial_capital
        )
        self.trades = []
        self.orders = []
        self.daily_values = []
        self.current_date = None

    def calculate_commission(self, amount: float) -> float:
        """计算佣金"""
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)

    def calculate_slippage(self, price: float, side: OrderSide) -> float:
        """计算滑点"""
        slippage = price * self.slippage_rate
        if side == OrderSide.BUY:
            return slippage  # 买入价格上滑
        else:
            return -slippage  # 卖出价格下滑

    def execute_order(
        self,
        order: Order,
        market_price: float
    ) -> Optional[Trade]:
        """执行订单"""
        # 计算滑点
        slippage = self.calculate_slippage(market_price, order.side)
        exec_price = market_price + slippage

        # 计算金额
        amount = order.quantity * exec_price

        # 计算佣金
        commission = self.calculate_commission(amount)

        # 检查资金/持仓
        if order.side == OrderSide.BUY:
            total_cost = amount + commission
            if total_cost > self.portfolio.cash:
                logger.warning(f"资金不足: 需要 {total_cost:.2f}, 可用 {self.portfolio.cash:.2f}")
                return None
        else:
            position = self.portfolio.get_position(order.symbol)
            if order.quantity > position.quantity:
                logger.warning(f"持仓不足: 需要 {order.quantity}, 持有 {position.quantity}")
                return None

        # 创建成交记录
        trade = Trade(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=exec_price,
            amount=amount,
            commission=commission,
            slippage=abs(slippage * order.quantity),
            timestamp=self.current_date
        )

        # 更新组合
        if order.side == OrderSide.BUY:
            self.portfolio.cash -= (amount + commission)
        else:
            self.portfolio.cash += (amount - commission)

        self.portfolio.total_commission += commission
        self.portfolio.total_slippage += trade.slippage

        # 更新持仓
        position = self.portfolio.get_position(order.symbol)
        position.update(trade, exec_price)

        # 记录
        self.trades.append(trade)
        self.orders.append(order)

        return trade

    def run(
        self,
        data: pd.DataFrame,
        signal_generator: Callable[[pd.DataFrame, int], int],
        position_sizer: Optional[Callable[[Portfolio, float, int], int]] = None
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            data: 行情数据 (需包含 date, open, high, low, close, volume 列)
            signal_generator: 信号生成函数 (data, index) -> signal (-1, 0, 1)
            position_sizer: 仓位计算函数 (portfolio, price, signal) -> quantity

        Returns:
            回测结果
        """
        logger.info("开始回测...")
        self.reset()

        # 默认仓位管理: 固定比例
        if position_sizer is None:
            def default_sizer(portfolio, price, signal):
                if signal != 0:
                    available = portfolio.cash * 0.95  # 95%资金可用
                    return int(available / price / 100) * 100  # 整百股
                return 0
            position_sizer = default_sizer

        # 获取symbol
        symbol = data['symbol'].iloc[0] if 'symbol' in data.columns else 'STOCK'

        # 遍历数据
        for i in range(len(data)):
            row = data.iloc[i]
            self.current_date = row['date'] if isinstance(row['date'], datetime) else pd.to_datetime(row['date'])
            current_price = row['close']

            # 更新持仓市值
            position = self.portfolio.get_position(symbol)
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = (current_price - position.avg_price) * position.quantity

            # 生成信号
            signal = signal_generator(data, i)

            # 执行交易
            if signal == 1 and position.quantity == 0:
                # 买入信号
                qty = position_sizer(self.portfolio, current_price, signal)
                if qty > 0:
                    order = Order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=qty,
                        price=current_price,
                        timestamp=self.current_date
                    )
                    self.execute_order(order, current_price)

            elif signal == -1 and position.quantity > 0:
                # 卖出信号
                order = Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    price=current_price,
                    timestamp=self.current_date
                )
                self.execute_order(order, current_price)

            # 记录每日净值
            self.daily_values.append({
                'date': self.current_date,
                'cash': self.portfolio.cash,
                'position_value': self.portfolio.market_value,
                'total_value': self.portfolio.total_value,
                'return': self.portfolio.total_return
            })

        # 计算结果
        results = self._calculate_results(data)

        logger.success(
            f"回测完成: 收益率={results['total_return']*100:.2f}%, "
            f"夏普比率={results['sharpe_ratio']:.2f}, "
            f"最大回撤={results['max_drawdown']*100:.2f}%"
        )

        return results

    def _calculate_results(self, data: pd.DataFrame) -> Dict[str, Any]:
        """计算回测指标"""
        df = pd.DataFrame(self.daily_values)

        # 基础指标
        total_return = self.portfolio.total_return
        total_pnl = self.portfolio.total_pnl

        # 日收益率
        df['daily_return'] = df['total_value'].pct_change()

        # 年化收益率
        trading_days = len(df)
        annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0

        # 波动率
        volatility = df['daily_return'].std() * np.sqrt(252)

        # 夏普比率
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0

        # 最大回撤
        df['cummax'] = df['total_value'].cummax()
        df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax']
        max_drawdown = df['drawdown'].min()

        # 最大回撤持续期
        drawdown_periods = (df['drawdown'] < 0).astype(int)
        max_drawdown_duration = 0
        current_duration = 0
        for val in drawdown_periods:
            if val == 1:
                current_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_duration)
            else:
                current_duration = 0

        # 胜率
        winning_trades = [t for t in self.trades if t.side == OrderSide.SELL and
                         t.price > self.portfolio.get_position(t.symbol).avg_price]
        total_trades = len([t for t in self.trades if t.side == OrderSide.SELL])
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        # 交易统计
        n_trades = len(self.trades)
        n_buy = len([t for t in self.trades if t.side == OrderSide.BUY])
        n_sell = len([t for t in self.trades if t.side == OrderSide.SELL])

        # 卡尔马比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 索提诺比率
        negative_returns = df['daily_return'][df['daily_return'] < 0]
        downside_std = negative_returns.std() * np.sqrt(252)
        sortino_ratio = annual_return / downside_std if downside_std > 0 else 0

        results = {
            # 收益指标
            'total_return': total_return,
            'annual_return': annual_return,
            'total_pnl': total_pnl,

            # 风险指标
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,

            # 风险调整收益
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,

            # 交易统计
            'total_trades': n_trades,
            'buy_trades': n_buy,
            'sell_trades': n_sell,
            'win_rate': win_rate,
            'total_commission': self.portfolio.total_commission,
            'total_slippage': self.portfolio.total_slippage,

            # 资金信息
            'initial_capital': self.initial_capital,
            'final_value': self.portfolio.total_value,

            # 日度数据
            'daily_values': df,
            'trades': self.trades
        }

        return results

    def get_trades_df(self) -> pd.DataFrame:
        """获取交易记录DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                'trade_id': t.trade_id,
                'timestamp': t.timestamp,
                'symbol': t.symbol,
                'side': t.side.value,
                'quantity': t.quantity,
                'price': t.price,
                'amount': t.amount,
                'commission': t.commission,
                'slippage': t.slippage
            }
            for t in self.trades
        ])


if __name__ == "__main__":
    # 测试代码
    logger.info("测试回测引擎")

    # 创建模拟数据
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2023-01-01', periods=n)

    # 模拟价格
    returns = np.random.randn(n) * 0.02
    price = 100 * np.exp(np.cumsum(returns))

    data = pd.DataFrame({
        'date': dates,
        'symbol': 'TEST',
        'open': price * (1 + np.random.randn(n) * 0.005),
        'high': price * (1 + np.abs(np.random.randn(n) * 0.01)),
        'low': price * (1 - np.abs(np.random.randn(n) * 0.01)),
        'close': price,
        'volume': np.random.randint(100000, 1000000, n)
    })

    # 简单移动平均策略
    def ma_signal(data, index):
        if index < 20:
            return 0
        ma5 = data['close'].iloc[index-5:index].mean()
        ma20 = data['close'].iloc[index-20:index].mean()

        if ma5 > ma20:
            return 1  # 买入
        elif ma5 < ma20:
            return -1  # 卖出
        return 0

    # 运行回测
    engine = BacktestEngine(initial_capital=1_000_000)
    results = engine.run(data, ma_signal)

    print("\n=== 回测结果 ===")
    for key in ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown',
                'win_rate', 'total_trades', 'total_commission']:
        value = results[key]
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    print(f"\n=== 交易记录 ({len(engine.trades)}笔) ===")
    trades_df = engine.get_trades_df()
    print(trades_df.head(10))
