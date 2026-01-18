"""
风险管理模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger
from scipy import stats


@dataclass
class RiskLimits:
    """风控限制"""
    max_position_size: float = 0.2        # 单只股票最大仓位
    max_portfolio_size: float = 0.95      # 最大总仓位
    max_drawdown_limit: float = 0.15      # 最大回撤限制
    max_leverage: float = 1.0             # 最大杠杆
    max_sector_exposure: float = 0.4      # 行业暴露限制
    max_single_loss: float = 0.02         # 单笔最大亏损
    daily_loss_limit: float = 0.03        # 日亏损限制
    stop_loss_pct: float = 0.05           # 止损比例
    take_profit_pct: float = 0.10         # 止盈比例


class RiskCalculator:
    """风险计算器"""

    @staticmethod
    def calculate_var(
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical"
    ) -> float:
        """
        计算VaR (Value at Risk)

        Args:
            returns: 收益率序列
            confidence_level: 置信水平
            method: 计算方法 ('historical', 'parametric', 'monte_carlo')

        Returns:
            VaR值
        """
        alpha = 1 - confidence_level

        if method == "historical":
            # 历史模拟法
            var = np.percentile(returns.dropna(), alpha * 100)

        elif method == "parametric":
            # 参数法 (假设正态分布)
            mu = returns.mean()
            sigma = returns.std()
            var = mu - stats.norm.ppf(confidence_level) * sigma

        elif method == "monte_carlo":
            # 蒙特卡洛模拟
            mu = returns.mean()
            sigma = returns.std()
            simulations = np.random.normal(mu, sigma, 10000)
            var = np.percentile(simulations, alpha * 100)

        else:
            raise ValueError(f"不支持的方法: {method}")

        return var

    @staticmethod
    def calculate_cvar(
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算CVaR (Conditional VaR / Expected Shortfall)

        Args:
            returns: 收益率序列
            confidence_level: 置信水平

        Returns:
            CVaR值
        """
        var = RiskCalculator.calculate_var(returns, confidence_level)
        cvar = returns[returns <= var].mean()
        return cvar if not np.isnan(cvar) else var

    @staticmethod
    def calculate_max_drawdown(values: pd.Series) -> Tuple[float, int, int]:
        """
        计算最大回撤

        Args:
            values: 净值序列

        Returns:
            (最大回撤, 开始索引, 结束索引)
        """
        cummax = values.cummax()
        drawdown = (values - cummax) / cummax

        max_dd = drawdown.min()
        end_idx = drawdown.idxmin()

        # 找到回撤开始点
        start_idx = values[:end_idx].idxmax()

        return max_dd, start_idx, end_idx

    @staticmethod
    def calculate_volatility(
        returns: pd.Series,
        window: int = 20,
        annualize: bool = True
    ) -> pd.Series:
        """
        计算滚动波动率

        Args:
            returns: 收益率序列
            window: 滚动窗口
            annualize: 是否年化

        Returns:
            波动率序列
        """
        vol = returns.rolling(window=window).std()

        if annualize:
            vol = vol * np.sqrt(252)

        return vol

    @staticmethod
    def calculate_beta(
        asset_returns: pd.Series,
        market_returns: pd.Series
    ) -> float:
        """
        计算Beta值

        Args:
            asset_returns: 资产收益率
            market_returns: 市场收益率

        Returns:
            Beta值
        """
        # 对齐数据
        aligned = pd.DataFrame({
            'asset': asset_returns,
            'market': market_returns
        }).dropna()

        if len(aligned) < 20:
            return 1.0

        covariance = aligned['asset'].cov(aligned['market'])
        market_variance = aligned['market'].var()

        return covariance / market_variance if market_variance > 0 else 1.0

    @staticmethod
    def calculate_correlation_matrix(
        returns_df: pd.DataFrame
    ) -> pd.DataFrame:
        """计算相关性矩阵"""
        return returns_df.corr()


class RiskMonitor:
    """风险监控"""

    def __init__(self, limits: Optional[RiskLimits] = None):
        """
        初始化

        Args:
            limits: 风控限制
        """
        self.limits = limits or RiskLimits()
        self.alerts: List[Dict[str, Any]] = []
        self.current_drawdown: float = 0.0
        self.daily_pnl: float = 0.0
        self.peak_value: float = 0.0

    def check_position_limit(
        self,
        position_value: float,
        portfolio_value: float,
        symbol: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查仓位限制

        Args:
            position_value: 持仓市值
            portfolio_value: 组合总值
            symbol: 股票代码

        Returns:
            (是否通过, 警告信息)
        """
        if portfolio_value <= 0:
            return False, "组合价值异常"

        position_ratio = position_value / portfolio_value

        if position_ratio > self.limits.max_position_size:
            msg = f"{symbol} 仓位 {position_ratio:.2%} 超过限制 {self.limits.max_position_size:.2%}"
            self._add_alert("POSITION_LIMIT", msg, "HIGH")
            return False, msg

        return True, None

    def check_drawdown_limit(
        self,
        current_value: float,
        peak_value: float
    ) -> Tuple[bool, Optional[str]]:
        """
        检查回撤限制

        Args:
            current_value: 当前净值
            peak_value: 历史峰值

        Returns:
            (是否通过, 警告信息)
        """
        if peak_value <= 0:
            return True, None

        self.current_drawdown = (current_value - peak_value) / peak_value

        if self.current_drawdown < -self.limits.max_drawdown_limit:
            msg = f"回撤 {-self.current_drawdown:.2%} 超过限制 {self.limits.max_drawdown_limit:.2%}"
            self._add_alert("DRAWDOWN_LIMIT", msg, "CRITICAL")
            return False, msg

        return True, None

    def check_stop_loss(
        self,
        entry_price: float,
        current_price: float,
        side: str = "long"
    ) -> Tuple[bool, Optional[str]]:
        """
        检查止损

        Args:
            entry_price: 入场价格
            current_price: 当前价格
            side: 方向 ('long' 或 'short')

        Returns:
            (是否触发止损, 信息)
        """
        if side == "long":
            loss_pct = (current_price - entry_price) / entry_price
        else:
            loss_pct = (entry_price - current_price) / entry_price

        if loss_pct < -self.limits.stop_loss_pct:
            msg = f"触发止损: 亏损 {-loss_pct:.2%} 超过 {self.limits.stop_loss_pct:.2%}"
            self._add_alert("STOP_LOSS", msg, "HIGH")
            return True, msg

        return False, None

    def check_take_profit(
        self,
        entry_price: float,
        current_price: float,
        side: str = "long"
    ) -> Tuple[bool, Optional[str]]:
        """
        检查止盈

        Args:
            entry_price: 入场价格
            current_price: 当前价格
            side: 方向

        Returns:
            (是否触发止盈, 信息)
        """
        if side == "long":
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price

        if profit_pct > self.limits.take_profit_pct:
            msg = f"触发止盈: 盈利 {profit_pct:.2%} 超过 {self.limits.take_profit_pct:.2%}"
            self._add_alert("TAKE_PROFIT", msg, "INFO")
            return True, msg

        return False, None

    def check_daily_loss(
        self,
        daily_pnl: float,
        portfolio_value: float
    ) -> Tuple[bool, Optional[str]]:
        """
        检查日亏损限制

        Args:
            daily_pnl: 日盈亏
            portfolio_value: 组合价值

        Returns:
            (是否通过, 警告信息)
        """
        if portfolio_value <= 0:
            return False, "组合价值异常"

        daily_loss_ratio = daily_pnl / portfolio_value

        if daily_loss_ratio < -self.limits.daily_loss_limit:
            msg = f"日亏损 {-daily_loss_ratio:.2%} 超过限制 {self.limits.daily_loss_limit:.2%}"
            self._add_alert("DAILY_LOSS", msg, "CRITICAL")
            return False, msg

        return True, None

    def _add_alert(self, alert_type: str, message: str, severity: str):
        """添加警报"""
        from datetime import datetime

        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now()
        }
        self.alerts.append(alert)
        logger.warning(f"[{severity}] {alert_type}: {message}")

    def get_alerts(self, severity: Optional[str] = None) -> List[Dict]:
        """获取警报"""
        if severity is None:
            return self.alerts
        return [a for a in self.alerts if a['severity'] == severity]

    def clear_alerts(self):
        """清除警报"""
        self.alerts = []


class StressTest:
    """压力测试"""

    def __init__(self, portfolio_returns: pd.Series):
        """
        初始化

        Args:
            portfolio_returns: 组合收益率
        """
        self.returns = portfolio_returns

    def historical_scenarios(self) -> Dict[str, float]:
        """
        历史情景分析

        Returns:
            各历史情景下的预期损失
        """
        scenarios = {
            '2008金融危机': -0.45,    # 2008年股市下跌
            '2015股灾': -0.35,         # 2015年A股股灾
            '2020疫情': -0.30,         # 2020年3月暴跌
            '黑色星期一': -0.22,       # 1987年
            '普通熊市': -0.20,         # 普通熊市
            '极端波动': -0.10          # 日内极端波动
        }

        # 计算组合在各情景下的损失
        beta = 1.0  # 假设beta=1
        results = {}
        for name, market_return in scenarios.items():
            portfolio_impact = market_return * beta
            results[name] = portfolio_impact

        return results

    def monte_carlo_simulation(
        self,
        n_simulations: int = 10000,
        horizon: int = 252
    ) -> Dict[str, float]:
        """
        蒙特卡洛模拟

        Args:
            n_simulations: 模拟次数
            horizon: 模拟期限(天)

        Returns:
            模拟结果统计
        """
        mu = self.returns.mean()
        sigma = self.returns.std()

        # 生成模拟路径
        random_returns = np.random.normal(mu, sigma, (n_simulations, horizon))
        cumulative_returns = np.exp(np.cumsum(random_returns, axis=1)) - 1

        # 计算终值分布
        final_returns = cumulative_returns[:, -1]

        results = {
            'mean': np.mean(final_returns),
            'std': np.std(final_returns),
            'percentile_5': np.percentile(final_returns, 5),
            'percentile_10': np.percentile(final_returns, 10),
            'percentile_25': np.percentile(final_returns, 25),
            'percentile_75': np.percentile(final_returns, 75),
            'percentile_95': np.percentile(final_returns, 95),
            'max_loss': np.min(final_returns),
            'max_gain': np.max(final_returns),
            'prob_loss': np.mean(final_returns < 0)
        }

        return results

    def sensitivity_analysis(
        self,
        factor_changes: Dict[str, float]
    ) -> Dict[str, float]:
        """
        敏感性分析

        Args:
            factor_changes: 因子变化 (如 {'利率': 0.01, '波动率': 0.05})

        Returns:
            各因子影响
        """
        # 简化的敏感性分析
        base_return = self.returns.mean() * 252  # 年化

        results = {}
        for factor, change in factor_changes.items():
            if factor == '利率':
                # 利率上升对股票负面
                impact = -change * 5  # 假设久期为5
            elif factor == '波动率':
                # 波动率上升增加风险
                impact = -change * 2
            elif factor == '汇率':
                impact = change * 0.3  # 部分影响
            else:
                impact = 0

            results[factor] = impact

        return results


class PortfolioRiskManager:
    """组合风险管理"""

    def __init__(
        self,
        limits: Optional[RiskLimits] = None
    ):
        self.limits = limits or RiskLimits()
        self.monitor = RiskMonitor(limits)
        self.calculator = RiskCalculator()

    def analyze_portfolio_risk(
        self,
        positions: Dict[str, float],
        returns_df: pd.DataFrame,
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        分析组合风险

        Args:
            positions: 持仓 {symbol: value}
            returns_df: 收益率DataFrame
            portfolio_value: 组合总值

        Returns:
            风险分析报告
        """
        report = {}

        # 仓位分析
        report['position_concentration'] = {}
        for symbol, value in positions.items():
            ratio = value / portfolio_value
            report['position_concentration'][symbol] = {
                'value': value,
                'ratio': ratio,
                'exceeds_limit': ratio > self.limits.max_position_size
            }

        # 总仓位
        total_position = sum(positions.values()) / portfolio_value
        report['total_position_ratio'] = total_position

        # 组合VaR
        if len(returns_df) > 0:
            # 简化: 使用等权重组合
            portfolio_returns = returns_df.mean(axis=1)

            report['var_95'] = self.calculator.calculate_var(portfolio_returns, 0.95)
            report['cvar_95'] = self.calculator.calculate_cvar(portfolio_returns, 0.95)
            report['volatility'] = portfolio_returns.std() * np.sqrt(252)

            # 相关性
            report['correlation_matrix'] = self.calculator.calculate_correlation_matrix(returns_df)

        return report

    def generate_risk_report(
        self,
        daily_values: pd.Series,
        trades: List = None
    ) -> Dict[str, Any]:
        """
        生成风险报告

        Args:
            daily_values: 每日净值
            trades: 交易记录

        Returns:
            风险报告
        """
        returns = daily_values.pct_change().dropna()

        report = {
            'var_analysis': {
                'var_95_historical': self.calculator.calculate_var(returns, 0.95, 'historical'),
                'var_95_parametric': self.calculator.calculate_var(returns, 0.95, 'parametric'),
                'var_99_historical': self.calculator.calculate_var(returns, 0.99, 'historical'),
                'cvar_95': self.calculator.calculate_cvar(returns, 0.95),
                'cvar_99': self.calculator.calculate_cvar(returns, 0.99)
            },
            'drawdown_analysis': {},
            'volatility_analysis': {
                'current_volatility': returns.std() * np.sqrt(252),
                'rolling_volatility': self.calculator.calculate_volatility(returns).iloc[-1]
            }
        }

        # 回撤分析
        max_dd, start_idx, end_idx = self.calculator.calculate_max_drawdown(daily_values)
        report['drawdown_analysis'] = {
            'max_drawdown': max_dd,
            'current_drawdown': (daily_values.iloc[-1] - daily_values.max()) / daily_values.max()
        }

        # 压力测试
        stress_test = StressTest(returns)
        report['stress_test'] = {
            'historical_scenarios': stress_test.historical_scenarios(),
            'monte_carlo': stress_test.monte_carlo_simulation(n_simulations=5000, horizon=21)
        }

        return report


# 初始化文件
def create_init():
    return """\"\"\"
交易服务模块初始化
\"\"\"
from .backtest import BacktestEngine, Order, Trade, Position, Portfolio
from .strategy import (
    BaseStrategy, MLStrategy, TechnicalStrategy,
    MomentumStrategy, MeanReversionStrategy,
    PositionManager, SignalCombiner
)
from .performance import PerformanceAnalyzer, PerformanceMetrics
from .risk import (
    RiskLimits, RiskCalculator, RiskMonitor,
    StressTest, PortfolioRiskManager
)

__all__ = [
    'BacktestEngine', 'Order', 'Trade', 'Position', 'Portfolio',
    'BaseStrategy', 'MLStrategy', 'TechnicalStrategy',
    'MomentumStrategy', 'MeanReversionStrategy',
    'PositionManager', 'SignalCombiner',
    'PerformanceAnalyzer', 'PerformanceMetrics',
    'RiskLimits', 'RiskCalculator', 'RiskMonitor',
    'StressTest', 'PortfolioRiskManager'
]
"""


if __name__ == "__main__":
    # 测试代码
    logger.info("测试风险管理模块")

    # 创建模拟数据
    np.random.seed(42)
    n = 252
    dates = pd.date_range('2024-01-01', periods=n)

    returns = pd.Series(
        np.random.randn(n) * 0.02 + 0.0003,
        index=dates
    )

    values = 1000000 * np.exp(np.cumsum(returns))
    values = pd.Series(values, index=dates)

    # VaR计算
    print("\n=== VaR分析 ===")
    var_95 = RiskCalculator.calculate_var(returns, 0.95)
    cvar_95 = RiskCalculator.calculate_cvar(returns, 0.95)
    print(f"VaR (95%): {var_95:.4%}")
    print(f"CVaR (95%): {cvar_95:.4%}")

    # 最大回撤
    print("\n=== 回撤分析 ===")
    max_dd, start, end = RiskCalculator.calculate_max_drawdown(values)
    print(f"最大回撤: {max_dd:.4%}")

    # 压力测试
    print("\n=== 压力测试 ===")
    stress = StressTest(returns)
    scenarios = stress.historical_scenarios()
    for name, impact in scenarios.items():
        print(f"{name}: {impact:.2%}")

    # 蒙特卡洛模拟
    print("\n=== 蒙特卡洛模拟 ===")
    mc_results = stress.monte_carlo_simulation(n_simulations=5000, horizon=21)
    print(f"期望收益: {mc_results['mean']:.2%}")
    print(f"5%分位数: {mc_results['percentile_5']:.2%}")
    print(f"亏损概率: {mc_results['prob_loss']:.2%}")

    # 风控监控
    print("\n=== 风控监控 ===")
    monitor = RiskMonitor()
    passed, msg = monitor.check_drawdown_limit(950000, 1000000)
    print(f"回撤检查: {'通过' if passed else '未通过'} - {msg or ''}")
