"""
回测绩效分析模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class PerformanceMetrics:
    """绩效指标数据类"""
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    monthly_return: float = 0.0
    daily_return_mean: float = 0.0

    # 风险指标
    volatility: float = 0.0
    downside_volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    var_95: float = 0.0
    cvar_95: float = 0.0

    # 风险调整收益
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    information_ratio: float = 0.0

    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    avg_holding_period: float = 0.0

    # 基准对比
    alpha: float = 0.0
    beta: float = 0.0
    correlation: float = 0.0


class PerformanceAnalyzer:
    """绩效分析器"""

    def __init__(self, risk_free_rate: float = 0.02):
        """
        初始化

        Args:
            risk_free_rate: 无风险利率 (年化)
        """
        self.risk_free_rate = risk_free_rate
        self.daily_rf = (1 + risk_free_rate) ** (1/252) - 1

    def analyze(
        self,
        daily_values: pd.DataFrame,
        trades: List = None,
        benchmark: Optional[pd.Series] = None
    ) -> PerformanceMetrics:
        """
        全面分析回测绩效

        Args:
            daily_values: 每日净值数据
            trades: 交易记录
            benchmark: 基准收益率序列

        Returns:
            绩效指标
        """
        metrics = PerformanceMetrics()

        # 确保有daily_return列
        if 'daily_return' not in daily_values.columns:
            daily_values['daily_return'] = daily_values['total_value'].pct_change()

        returns = daily_values['daily_return'].dropna()

        # 收益指标
        self._calculate_returns(metrics, daily_values, returns)

        # 风险指标
        self._calculate_risk(metrics, returns)

        # 风险调整收益
        self._calculate_risk_adjusted(metrics, returns)

        # 交易统计
        if trades:
            self._calculate_trade_stats(metrics, trades)

        # 基准对比
        if benchmark is not None:
            self._calculate_benchmark_comparison(metrics, returns, benchmark)

        return metrics

    def _calculate_returns(
        self,
        metrics: PerformanceMetrics,
        daily_values: pd.DataFrame,
        returns: pd.Series
    ):
        """计算收益指标"""
        # 总收益
        initial_value = daily_values['total_value'].iloc[0]
        final_value = daily_values['total_value'].iloc[-1]
        metrics.total_return = (final_value - initial_value) / initial_value

        # 年化收益
        trading_days = len(returns)
        metrics.annual_return = (1 + metrics.total_return) ** (252 / trading_days) - 1

        # 月化收益
        metrics.monthly_return = (1 + metrics.total_return) ** (21 / trading_days) - 1

        # 日均收益
        metrics.daily_return_mean = returns.mean()

    def _calculate_risk(self, metrics: PerformanceMetrics, returns: pd.Series):
        """计算风险指标"""
        # 波动率 (年化)
        metrics.volatility = returns.std() * np.sqrt(252)

        # 下行波动率
        negative_returns = returns[returns < 0]
        metrics.downside_volatility = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        metrics.max_drawdown = drawdown.min()

        # 最大回撤持续期
        is_drawdown = drawdown < 0
        dd_periods = is_drawdown.astype(int).groupby((~is_drawdown).cumsum()).sum()
        metrics.max_drawdown_duration = int(dd_periods.max()) if len(dd_periods) > 0 else 0

        # VaR (95%)
        metrics.var_95 = np.percentile(returns, 5)

        # CVaR (95%)
        var_threshold = metrics.var_95
        metrics.cvar_95 = returns[returns <= var_threshold].mean() if len(returns[returns <= var_threshold]) > 0 else var_threshold

    def _calculate_risk_adjusted(
        self,
        metrics: PerformanceMetrics,
        returns: pd.Series
    ):
        """计算风险调整收益"""
        excess_returns = returns - self.daily_rf

        # 夏普比率
        if returns.std() > 0:
            metrics.sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
        else:
            metrics.sharpe_ratio = 0

        # 索提诺比率
        if metrics.downside_volatility > 0:
            metrics.sortino_ratio = (metrics.annual_return - self.risk_free_rate) / metrics.downside_volatility
        else:
            metrics.sortino_ratio = 0

        # 卡尔马比率
        if metrics.max_drawdown != 0:
            metrics.calmar_ratio = metrics.annual_return / abs(metrics.max_drawdown)
        else:
            metrics.calmar_ratio = 0

        # Omega比率
        threshold = 0
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns < threshold].sum())
        metrics.omega_ratio = gains / losses if losses > 0 else float('inf')

    def _calculate_trade_stats(
        self,
        metrics: PerformanceMetrics,
        trades: List
    ):
        """计算交易统计"""
        if not trades:
            return

        # 计算每笔交易的盈亏
        trade_pnls = []
        buy_price = None

        for trade in trades:
            if trade.side.value == 'buy':
                buy_price = trade.price
            elif trade.side.value == 'sell' and buy_price is not None:
                pnl = (trade.price - buy_price) / buy_price
                trade_pnls.append(pnl)
                buy_price = None

        if not trade_pnls:
            return

        trade_pnls = np.array(trade_pnls)

        metrics.total_trades = len(trade_pnls)
        metrics.winning_trades = np.sum(trade_pnls > 0)
        metrics.losing_trades = np.sum(trade_pnls < 0)
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0

        # 盈亏统计
        wins = trade_pnls[trade_pnls > 0]
        losses = trade_pnls[trade_pnls < 0]

        metrics.avg_win = wins.mean() if len(wins) > 0 else 0
        metrics.avg_loss = losses.mean() if len(losses) > 0 else 0
        metrics.max_win = wins.max() if len(wins) > 0 else 0
        metrics.max_loss = losses.min() if len(losses) > 0 else 0

        # 盈亏比
        total_wins = wins.sum() if len(wins) > 0 else 0
        total_losses = abs(losses.sum()) if len(losses) > 0 else 0
        metrics.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

    def _calculate_benchmark_comparison(
        self,
        metrics: PerformanceMetrics,
        returns: pd.Series,
        benchmark: pd.Series
    ):
        """计算基准对比指标"""
        # 对齐数据
        aligned = pd.DataFrame({
            'strategy': returns,
            'benchmark': benchmark
        }).dropna()

        if len(aligned) < 10:
            return

        strategy_returns = aligned['strategy']
        benchmark_returns = aligned['benchmark']

        # 相关性
        metrics.correlation = strategy_returns.corr(benchmark_returns)

        # Beta
        covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        metrics.beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

        # Alpha (CAPM)
        strategy_annual = (1 + strategy_returns.mean()) ** 252 - 1
        benchmark_annual = (1 + benchmark_returns.mean()) ** 252 - 1
        metrics.alpha = strategy_annual - (self.risk_free_rate + metrics.beta * (benchmark_annual - self.risk_free_rate))

        # 信息比率
        tracking_error = (strategy_returns - benchmark_returns).std() * np.sqrt(252)
        if tracking_error > 0:
            metrics.information_ratio = (strategy_annual - benchmark_annual) / tracking_error
        else:
            metrics.information_ratio = 0

    def generate_report(self, metrics: PerformanceMetrics) -> str:
        """生成绩效报告"""
        report = """
╔══════════════════════════════════════════════════════════════╗
║                     策略绩效分析报告                          ║
╠══════════════════════════════════════════════════════════════╣

◆ 收益指标
├─ 总收益率:          {total_return:>10.2%}
├─ 年化收益率:        {annual_return:>10.2%}
├─ 月化收益率:        {monthly_return:>10.2%}
└─ 日均收益率:        {daily_return:>10.4%}

◆ 风险指标
├─ 年化波动率:        {volatility:>10.2%}
├─ 下行波动率:        {downside_vol:>10.2%}
├─ 最大回撤:          {max_dd:>10.2%}
├─ 回撤持续期:        {dd_duration:>10d} 天
├─ VaR (95%):         {var:>10.2%}
└─ CVaR (95%):        {cvar:>10.2%}

◆ 风险调整收益
├─ 夏普比率:          {sharpe:>10.2f}
├─ 索提诺比率:        {sortino:>10.2f}
├─ 卡尔马比率:        {calmar:>10.2f}
└─ Omega比率:         {omega:>10.2f}

◆ 交易统计
├─ 总交易次数:        {total_trades:>10d}
├─ 盈利次数:          {win_trades:>10d}
├─ 亏损次数:          {loss_trades:>10d}
├─ 胜率:              {win_rate:>10.2%}
├─ 盈亏比:            {profit_factor:>10.2f}
├─ 平均盈利:          {avg_win:>10.2%}
├─ 平均亏损:          {avg_loss:>10.2%}
├─ 最大单笔盈利:      {max_win:>10.2%}
└─ 最大单笔亏损:      {max_loss:>10.2%}

◆ 基准对比
├─ Alpha:             {alpha:>10.2%}
├─ Beta:              {beta:>10.2f}
└─ 相关系数:          {correlation:>10.2f}

╚══════════════════════════════════════════════════════════════╝
        """.format(
            total_return=metrics.total_return,
            annual_return=metrics.annual_return,
            monthly_return=metrics.monthly_return,
            daily_return=metrics.daily_return_mean,
            volatility=metrics.volatility,
            downside_vol=metrics.downside_volatility,
            max_dd=metrics.max_drawdown,
            dd_duration=metrics.max_drawdown_duration,
            var=metrics.var_95,
            cvar=metrics.cvar_95,
            sharpe=metrics.sharpe_ratio,
            sortino=metrics.sortino_ratio,
            calmar=metrics.calmar_ratio,
            omega=min(metrics.omega_ratio, 99.99),
            total_trades=metrics.total_trades,
            win_trades=metrics.winning_trades,
            loss_trades=metrics.losing_trades,
            win_rate=metrics.win_rate,
            profit_factor=min(metrics.profit_factor, 99.99),
            avg_win=metrics.avg_win,
            avg_loss=metrics.avg_loss,
            max_win=metrics.max_win,
            max_loss=metrics.max_loss,
            alpha=metrics.alpha,
            beta=metrics.beta,
            correlation=metrics.correlation
        )

        return report

    def to_dict(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'returns': {
                'total_return': metrics.total_return,
                'annual_return': metrics.annual_return,
                'monthly_return': metrics.monthly_return,
                'daily_return_mean': metrics.daily_return_mean
            },
            'risk': {
                'volatility': metrics.volatility,
                'downside_volatility': metrics.downside_volatility,
                'max_drawdown': metrics.max_drawdown,
                'max_drawdown_duration': metrics.max_drawdown_duration,
                'var_95': metrics.var_95,
                'cvar_95': metrics.cvar_95
            },
            'risk_adjusted': {
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'omega_ratio': metrics.omega_ratio
            },
            'trading': {
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor,
                'avg_win': metrics.avg_win,
                'avg_loss': metrics.avg_loss
            },
            'benchmark': {
                'alpha': metrics.alpha,
                'beta': metrics.beta,
                'correlation': metrics.correlation
            }
        }


if __name__ == "__main__":
    # 测试代码
    logger.info("测试绩效分析模块")

    # 创建模拟数据
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2023-01-01', periods=n)

    # 模拟策略净值
    returns = np.random.randn(n) * 0.02 + 0.0005  # 有正偏的收益
    cumulative_value = 1000000 * np.exp(np.cumsum(returns))

    daily_values = pd.DataFrame({
        'date': dates,
        'total_value': cumulative_value,
        'daily_return': returns
    })

    # 模拟基准
    benchmark_returns = np.random.randn(n) * 0.015 + 0.0003
    benchmark = pd.Series(benchmark_returns, index=range(n))

    # 分析
    analyzer = PerformanceAnalyzer()
    metrics = analyzer.analyze(daily_values, benchmark=benchmark)

    # 打印报告
    report = analyzer.generate_report(metrics)
    print(report)
