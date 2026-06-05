"""
DLQI 统一特征工程 — 24 维 A 股技术指标
被 scripts/train_cn_models.py、scripts/train_champion.py、scripts/run_pipeline.py 共享，
避免多处复制粘贴的特征定义漂移。

V1 (legacy, 12 features) — 与老版模型兼容的最小特征集。
V2 (champion, 24 features) — 冠军 Transformer 使用的扩展特征集。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLS_V1: list[str] = [
    "open", "high", "low", "close", "volume",
    "returns", "ma_5", "ma_20",
    "volatility", "rsi", "macd", "macd_signal",
]


FEATURE_COLS_V2: list[str] = [
    # 价格与成交量 (5)
    "open", "high", "low", "close", "volume",
    # 收益率与均线 (4)
    "returns", "ma_5", "ma_20", "ma_ratio",
    # 波动率家族 (3)
    "volatility", "atr_14", "bb_width",
    # 均值回归信号 (2)
    "bb_upper_dist", "bb_lower_dist",
    # 动量 (3)
    "rsi", "kdj_k", "kdj_d",
    # 趋势强度 (2)
    "macd", "macd_signal",
    # 价格/均线相对位置 (1)
    "price_ma20_gap",
    # 成交量 (3)
    "volume_ma5", "vol_ratio", "obv_norm",
    # 方向强度 (1)
    "adx_14",
]
assert len(FEATURE_COLS_V2) == 24, f"expected 24 features, got {len(FEATURE_COLS_V2)}"


def engineer_features_v1(df: pd.DataFrame) -> pd.DataFrame:
    """老版 12 特征 — 与 scripts/train_cn_models.py、run_pipeline.py 逐字对齐。"""
    df = df.copy()
    df["returns"] = df["close"].pct_change()
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["volatility"] = df["returns"].rolling(20).std()
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-10)))
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    return df.dropna().reset_index(drop=True)


def _kdj(df: pd.DataFrame, n: int = 9) -> tuple[pd.Series, pd.Series]:
    """KDJ 9-3-3 — K/D 线（J 信息与 K/D 高度相关，暂不加入特征集）。"""
    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n + 1e-10) * 100
    k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    d = k.ewm(alpha=1 / 3, adjust=False).mean()
    return k, d


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """平均真实波幅 ATR(14)。"""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - close_prev).abs(),
            (low - close_prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n).mean()


def _adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """ADX(14) — 趋势强度指标，简化实现。"""
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)
    atr = _atr(df, n)
    plus_di = 100 * plus_dm.ewm(span=n, adjust=False).mean() / (atr + 1e-10)
    minus_di = 100 * minus_dm.ewm(span=n, adjust=False).mean() / (atr + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    return dx.ewm(span=n, adjust=False).mean()


def _obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume（标准化版本，用 z-score 防止长周期漂移淹没短周期信号）。"""
    direction = np.sign(df["close"].diff()).fillna(0)
    obv = (direction * df["volume"]).cumsum()
    # 20 日滚动 z-score 标准化
    mean = obv.rolling(60, min_periods=20).mean()
    std = obv.rolling(60, min_periods=20).std()
    return (obv - mean) / (std + 1e-10)


def engineer_features_v2(df: pd.DataFrame) -> pd.DataFrame:
    """冠军 24 特征集 — 包含价格/成交量/动量/波动率/趋势强度多个维度。

    输入 df 必须包含 [date, open, high, low, close, volume] 列。
    返回按时间单调递增且剔除了 warmup NaN 的 DataFrame。
    """
    df = df.copy()

    # --- 收益率 + 均线 ---
    df["returns"] = df["close"].pct_change()
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_ratio"] = df["ma_5"] / (df["ma_20"] + 1e-10)
    df["price_ma20_gap"] = (df["close"] - df["ma_20"]) / (df["ma_20"] + 1e-10)

    # --- 波动率 ---
    df["volatility"] = df["returns"].rolling(20).std()
    df["atr_14"] = _atr(df, 14)

    # --- 布林带 (20, 2σ) ---
    bb_mid = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    df["bb_width"] = (bb_upper - bb_lower) / (bb_mid + 1e-10)
    df["bb_upper_dist"] = (bb_upper - df["close"]) / (df["close"] + 1e-10)
    df["bb_lower_dist"] = (df["close"] - bb_lower) / (df["close"] + 1e-10)

    # --- 动量 ---
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-10)))

    k, d = _kdj(df, 9)
    df["kdj_k"] = k
    df["kdj_d"] = d

    # --- 趋势强度 ---
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["adx_14"] = _adx(df, 14)

    # --- 成交量 ---
    df["volume_ma5"] = df["volume"].rolling(5).mean()
    df["vol_ratio"] = df["volume"] / (df["volume"].rolling(20).mean() + 1e-10)
    df["obv_norm"] = _obv(df)

    return df.dropna().reset_index(drop=True)


__all__ = [
    "FEATURE_COLS_V1",
    "FEATURE_COLS_V2",
    "engineer_features_v1",
    "engineer_features_v2",
]
