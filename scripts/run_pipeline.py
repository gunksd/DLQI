#!/usr/bin/env python3
"""
DLQI 回测 Pipeline — 加载已训练模型，对每个模型在测试集上做回测，
汇总成排行榜 + 冠军分析 + 消融实验。

用法：
  # 默认：对 data/models/* 里所有模型跑回测
  backend/venv/bin/python scripts/run_pipeline.py

  # 冠军模型消融实验（使用已训练的 champion_transformer_*）
  backend/venv/bin/python scripts/run_pipeline.py --ablation

A 股适配要点：
  - T+1 强制：买入当日下标 i 最早能卖的日期是 i+1
  - 非对称费率：买 = 佣金万2.5 + 滑点0.1% = 0.00125
                卖 = 佣金万2.5 + 印花税0.05% + 滑点0.1% = 0.00175
  - 冠军模型使用学到的阈值 τ* + 置信度过滤（softmax_up > 0.55 才开仓）
  - 旧模型使用 pred > 0 的原始阈值
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import math
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from common_features import (  # noqa: E402
    FEATURE_COLS_V1,
    FEATURE_COLS_V2,
    engineer_features_v1,
    engineer_features_v2,
)

DATA_DIR = ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
RAW_DIR = DATA_DIR / "raw"
RESULTS_DIR = ROOT / "results"
CURVES_DIR = RESULTS_DIR / "equity_curves"
CURVES_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SYMBOLS_ALL = ["600519", "601318", "600036", "300750", "002594"]
SEQ_LEN = 60
INITIAL_CAPITAL = 1_000_000.0

# A 股非对称费率
COST_BUY = 0.00125   # 佣金万2.5 + 滑点0.1%
COST_SELL = 0.00175  # 佣金万2.5 + 印花税0.05% + 滑点0.1%

MAX_HOLD_DAYS = 10
STOP_LOSS = -0.08          # 硬止损放宽到 -8%（追踪止盈承担主要止盈职责）
TAKE_PROFIT = 0.30         # 极端行情兜底（追踪止盈正常情况下先触发）
TRAILING_STOP = 0.05       # 追踪止盈：从持仓最高价回撤 5% 平仓
CONSECUTIVE_LOSS_PAUSE = 2 # 连亏 N 日后暂停买入 1 日（净值动量风控）
DRAWDOWN_REDUCE = 0.08     # 组合净值从高点回撤超此值仓位减半
CONFIDENCE_FLOOR = 0.55    # 冠军模型的上涨概率阈值

# 测试集时间范围（与 train_champion.py 一致）
TEST_START = "2021-01-01"  # 2021 起为测试集（覆盖 2021 牛尾 + 2022 熊市 + 2023-2025 震荡）


# =========================================================
# 模型架构（与 train_*.py 对齐）
# =========================================================

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size, hidden_size=hidden_size,
            num_layers=num_layers, dropout=dropout if num_layers > 1 else 0,
            batch_first=True, bidirectional=True,
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2, num_heads=4, dropout=dropout, batch_first=True,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        return self.fc(attn_out[:, -1, :])


class TransformerRegressor(nn.Module):
    """回归版 Transformer（老 train_cn_models.py 的 TransformerModel）。"""
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.2):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(500, d_model)
        position = torch.arange(0, 500, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
        )

    def forward(self, x):
        seq_len = x.size(1)
        x = self.input_proj(x)
        x = x + self.pe[:, :seq_len, :]
        mask = nn.Transformer.generate_square_subsequent_mask(seq_len, device=x.device)
        x = self.transformer(x, mask=mask)
        return self.fc(x[:, -1, :])


class TransformerClassifierLegacy(nn.Module):
    """老 train_cn_models.py 的分类 Transformer（d_model=64, 4 heads, 2 layers）。"""
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.3):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(500, d_model)
        position = torch.arange(0, 500, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_model // 2, 2),
        )

    def forward(self, x):
        seq_len = x.size(1)
        x = self.input_proj(x)
        x = x + self.pe[:, :seq_len, :]
        mask = nn.Transformer.generate_square_subsequent_mask(seq_len, device=x.device)
        x = self.transformer(x, mask=mask)
        return self.fc(x[:, -1, :])


class TransformerModel(nn.Module):
    """多股联合 Transformer 分类器（与 train_champion.py 对齐）。输出 shape = (B, 2) logits。"""
    def __init__(self, input_size, d_model=128, nhead=8, num_layers=3, dropout=0.3, seq_len=SEQ_LEN):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(seq_len, d_model)
        position = torch.arange(0, seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True, activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_model // 2, 2),
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = x + self.pe[:, :x.size(1), :]
        mask = nn.Transformer.generate_square_subsequent_mask(x.size(1), device=x.device)
        x = self.transformer(x, mask=mask)
        x = self.norm(x[:, -1, :])
        return self.head(x)


class TransformerModelV2(nn.Module):
    """v2 变体，属性名为 proj/enc（与 TransformerModel 的 input_proj/transformer 不同）。"""
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.2, seq_len=SEQ_LEN):
        super().__init__()
        self.proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(seq_len, d_model)
        position = torch.arange(0, seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True, activation="gelu",
        )
        self.enc = nn.TransformerEncoder(encoder_layer, num_layers)
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_model // 2, 2),
        )

    def forward(self, x):
        x = self.proj(x)
        x = x + self.pe[:, :x.size(1), :]
        mask = nn.Transformer.generate_square_subsequent_mask(x.size(1), device=x.device)
        x = self.enc(x, mask=mask)
        x = self.norm(x[:, -1, :])
        return self.head(x)


def _build_primary_model(meta: dict, input_size: int, model_path: Path = None):
    cfg = meta.get("best_config", {})
    # 通过 state_dict keys 自动判断用哪个架构
    if model_path is not None:
        keys = list(torch.load(model_path, map_location="cpu", weights_only=True).keys())
        if any(k.startswith("proj.") or k.startswith("enc.") for k in keys):
            return TransformerModelV2(
                input_size=input_size,
                d_model=cfg.get("d_model", 64),
                nhead=cfg.get("nhead", 4),
                num_layers=cfg.get("num_layers", 2),
                dropout=cfg.get("dropout", 0.2),
                seq_len=meta.get("seq_len", SEQ_LEN),
            )
    return TransformerModel(
        input_size=input_size,
        d_model=cfg.get("d_model", 128),
        nhead=cfg.get("nhead", 8),
        num_layers=cfg.get("num_layers", 3),
        dropout=cfg.get("dropout", 0.3),
        seq_len=meta.get("seq_len", SEQ_LEN),
    )


# =========================================================
# 模型加载/预测
# =========================================================

def load_model(model_dir: Path):
    meta = json.loads((model_dir / "metadata.json").read_text())
    model_type = meta["model_type"]
    features = meta.get("features", FEATURE_COLS_V1)
    input_size = len(features)
    scaler = joblib.load(model_dir / "scaler.pkl")

    if meta.get("is_champion") or meta.get("is_primary"):
        model = _build_primary_model(meta, input_size, model_dir / "model.pt")
        state = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        model.load_state_dict(state)
        model.to(DEVICE).eval()
    elif model_type == "lstm":
        model = LSTMModel(input_size=input_size)
        state = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        model.load_state_dict(state)
        model.to(DEVICE).eval()
    elif model_type == "transformer":
        task = meta.get("task_type", "regression")
        if task == "classification":
            model = TransformerClassifierLegacy(input_size=input_size)
        else:
            model = TransformerRegressor(input_size=input_size)
        state = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        model.load_state_dict(state)
        model.to(DEVICE).eval()
    elif model_type == "lightgbm":
        import lightgbm as lgb
        model = lgb.Booster(model_file=str(model_dir / "model.txt"))
    elif model_type == "xgboost":
        import xgboost as xgb
        model = xgb.Booster()
        model.load_model(str(model_dir / "model.json"))
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    return model, scaler, meta


def predict(model, meta: dict, X_seq: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    """返回 (signal, prob_up)。prob_up 仅在分类模型上有效，否则 None。"""
    model_type = meta["model_type"]
    is_champion = bool(meta.get("is_champion"))
    task = meta.get("task_type", "regression")

    if model_type in ("lstm", "transformer"):
        with torch.no_grad():
            t = torch.from_numpy(X_seq.astype(np.float32)).to(DEVICE)
            outputs = []
            probs = []
            for i in range(0, len(t), 256):
                out = model(t[i:i + 256])
                if task == "classification" or is_champion:
                    p = F.softmax(out, dim=1)[:, 1]
                    probs.append(p.cpu().numpy())
                    outputs.append((p - 0.5).cpu().numpy())  # 有符号 signal
                else:
                    outputs.append(out.squeeze(-1).cpu().numpy())
            signal = np.concatenate(outputs)
            prob_up = np.concatenate(probs) if probs else None
            return signal, prob_up
    elif model_type == "lightgbm":
        return model.predict(X_seq.reshape(X_seq.shape[0], -1)), None
    elif model_type == "xgboost":
        import xgboost as xgb
        return model.predict(xgb.DMatrix(X_seq.reshape(X_seq.shape[0], -1))), None
    return np.zeros(len(X_seq)), None


# =========================================================
# 回测引擎
# =========================================================

def run_backtest(
    signals: np.ndarray,
    prob_up: np.ndarray | None,
    returns: np.ndarray,
    prices: np.ndarray,
    dates: list,
    *,
    buy_threshold: float = 0.0,
    sell_threshold: float = 0.0,
    confidence_floor: float | None = None,
    enforce_t_plus_1: bool = True,
    cost_buy: float = COST_BUY,
    cost_sell: float = COST_SELL,
    max_hold: int = MAX_HOLD_DAYS,
    stop_loss: float = STOP_LOSS,
    take_profit: float = TAKE_PROFIT,
    trailing_stop: float = TRAILING_STOP,
    consecutive_loss_pause: int = CONSECUTIVE_LOSS_PAUSE,
    drawdown_reduce: float = DRAWDOWN_REDUCE,
    initial_capital: float = INITIAL_CAPITAL,
) -> dict:
    """
    - signals: 原始信号；对于冠军分类器是 prob_up-0.5，对于回归是预测收益。
    - prob_up: 分类器上涨概率；用于置信度过滤。None 时跳过。
    - buy_threshold / sell_threshold 在 signals 空间里的阈值。
    - enforce_t_plus_1: 买入当日不能卖出。
    - trailing_stop: 追踪止盈，持仓最高价回撤 5% 平仓
    - consecutive_loss_pause: 连亏 N 日暂停买入 1 日
    - drawdown_reduce: 净值高点回撤超此值后开仓资金减半
    """
    n = len(signals)
    capital = initial_capital
    position = 0  # 0=空仓, 1=持仓
    hold_days = 0
    entry_capital = capital
    entry_day = -1  # T+1 标记：最后一次开仓的日期索引
    position_high_price = 0.0  # 持仓期间最高收盘价（追踪止盈基准）

    # 净值动量风控状态
    peak_equity = initial_capital
    consecutive_loss_days = 0
    skip_buy_today = False
    position_size = 1.0   # 1.0=全仓, 0.5=半仓

    portfolio = [capital]
    benchmark = [initial_capital]
    daily_returns = [0.0]
    trades = []
    bench_capital = initial_capital
    prev_capital = capital

    for i in range(n):
        ret = float(returns[i]) if not np.isnan(returns[i]) else 0.0
        bench_capital *= (1 + ret)
        benchmark.append(bench_capital)

        # ====== 净值动量风控（每日开盘前根据昨日净值更新） ======
        # 仓位规模：净值从高点回撤超阈值则减半
        peak_equity = max(peak_equity, prev_capital)
        if prev_capital / peak_equity - 1.0 < -drawdown_reduce:
            position_size = 0.5
        else:
            position_size = 1.0

        # 连亏暂停
        if skip_buy_today:
            buy_blocked_today = True
            skip_buy_today = False  # 仅暂停 1 日
        else:
            buy_blocked_today = False

        # ====== 风险平仓检查（止损/固定止盈/追踪止盈/最大持仓） ======
        should_close_by_risk = False
        close_reason = None
        if position == 1:
            hold_days += 1
            position_high_price = max(position_high_price, float(prices[i]))
            pnl_pct = (capital - entry_capital) / entry_capital if entry_capital else 0
            # 追踪止盈：相对持仓期最高价回撤
            trailing_drawdown = float(prices[i]) / position_high_price - 1.0 if position_high_price > 0 else 0
            if pnl_pct <= stop_loss:
                should_close_by_risk = True
                close_reason = "stop_loss"
            elif pnl_pct >= take_profit:
                should_close_by_risk = True
                close_reason = "take_profit"
            elif trailing_drawdown <= -trailing_stop:
                should_close_by_risk = True
                close_reason = "trailing_stop"
            elif hold_days >= max_hold:
                should_close_by_risk = True
                close_reason = "max_hold"

        # 模型信号
        sig = float(signals[i])
        buy_signal = sig > buy_threshold
        sell_signal = sig <= sell_threshold

        # 置信度过滤（仅冠军使用 prob_up）
        if confidence_floor is not None and prob_up is not None:
            if buy_signal and prob_up[i] < confidence_floor:
                buy_signal = False

        # 净值动量风控：连亏暂停日不允许新开仓
        if buy_blocked_today:
            buy_signal = False

        # T+1：买入后立即封锁卖出当日
        can_sell_today = (not enforce_t_plus_1) or (entry_day < 0) or (i > entry_day)

        # 卖出动作
        if position == 1 and (sell_signal or should_close_by_risk) and can_sell_today:
            capital *= (1 - cost_sell)
            position = 0
            hold_days = 0
            position_high_price = 0.0
            trades.append({
                "date": str(dates[i]),
                "action": "sell",
                "price": round(float(prices[i]), 2),
                "cost": round(capital * cost_sell / (1 - cost_sell), 2),
                "reason": close_reason or "signal",
            })

        # 买入动作（按 position_size 缩放，半仓时只用一半资金）
        elif position == 0 and buy_signal:
            invest_capital = capital * position_size
            cash_reserve = capital - invest_capital
            invest_capital *= (1 - cost_buy)
            capital = invest_capital + cash_reserve
            position = 1
            hold_days = 0
            entry_capital = capital
            entry_day = i
            position_high_price = float(prices[i])
            trades.append({
                "date": str(dates[i]),
                "action": "buy",
                "price": round(float(prices[i]), 2),
                "cost": round(invest_capital * cost_buy / (1 - cost_buy), 2),
                "position_size": position_size,
            })

        # 日终标记持仓浮动
        if position == 1:
            # 若半仓买入，仅持仓部分参与日内收益
            held_value = capital * position_size if position_size < 1.0 else capital
            cash = capital - held_value if position_size < 1.0 else 0.0
            held_value *= (1 + ret)
            capital = held_value + cash
            daily_returns.append(ret * (1 if position_size >= 1.0 else position_size))
        else:
            daily_returns.append(0.0)

        portfolio.append(capital)

        # ====== 净值动量统计（连亏天数） ======
        daily_pnl = (capital / prev_capital - 1.0) if prev_capital > 0 else 0.0
        if daily_pnl < -0.005:  # 当日亏损 > 0.5% 算亏损日
            consecutive_loss_days += 1
        else:
            consecutive_loss_days = 0
        if consecutive_loss_days >= consecutive_loss_pause:
            skip_buy_today = True  # 明日暂停买入
            consecutive_loss_days = 0  # 重置
        prev_capital = capital

    return {
        "portfolio": np.array(portfolio),
        "benchmark": np.array(benchmark),
        "daily_returns": np.array(daily_returns),
        "trades": trades,
    }


def calculate_metrics(bt: dict, initial_capital: float = INITIAL_CAPITAL) -> dict:
    portfolio = bt["portfolio"]
    benchmark = bt["benchmark"]
    dr = bt["daily_returns"][1:]
    trades = bt["trades"]

    total_return = (portfolio[-1] / initial_capital) - 1
    n_days = max(len(portfolio) - 1, 1)
    annual_return = (1 + total_return) ** (252 / n_days) - 1
    volatility = float(np.std(dr) * np.sqrt(252)) if len(dr) > 1 else 0.0
    sharpe = annual_return / volatility if volatility > 0 else 0.0

    downside = dr[dr < 0]
    down_vol = float(np.std(downside) * np.sqrt(252)) if len(downside) > 1 else 0.0
    sortino = annual_return / down_vol if down_vol > 0 else 0.0

    peak = np.maximum.accumulate(portfolio)
    dd = (portfolio - peak) / peak
    max_drawdown = float(np.min(dd)) if len(dd) else 0.0
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    buys = [t for t in trades if t["action"] == "buy"]
    sells = [t for t in trades if t["action"] == "sell"]
    n_round_trips = min(len(buys), len(sells))
    wins = sum(1 for i in range(n_round_trips) if sells[i]["price"] > buys[i]["price"])
    win_rate = wins / n_round_trips if n_round_trips else 0.0

    gains = float(dr[dr > 0].sum())
    losses = abs(float(dr[dr < 0].sum()))
    profit_factor = gains / losses if losses > 0 else float("inf")

    bench_return = (benchmark[-1] / initial_capital) - 1
    total_commission = sum(t.get("cost", 0) for t in trades)

    return {
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "n_trades": len(trades),
        "total_commission": total_commission,
        "benchmark_return": float(bench_return),
        "excess_return": float(total_return - bench_return),
    }


# =========================================================
# 单模型回测
# =========================================================

def _feature_function(features: list[str]):
    """根据 metadata.features 推断用 v1 还是 v2。"""
    if len(features) == len(FEATURE_COLS_V2) and features == FEATURE_COLS_V2:
        return engineer_features_v2, FEATURE_COLS_V2
    return engineer_features_v1, FEATURE_COLS_V1


def backtest_for_symbol(model, scaler, meta: dict, symbol: str, test_ratio: float = 0.15) -> dict | None:
    """对 symbol 的测试段做回测。

    优先使用 TEST_START 时间切分（2021-01-01 起），与训练集严格对齐；
    若数据不足则退回到 test_ratio 比例切分。
    """
    csv = RAW_DIR / f"cn_{symbol}.csv"
    if not csv.exists():
        return None
    df = pd.read_csv(csv)
    eng_fn, feat_cols = _feature_function(meta.get("features", FEATURE_COLS_V1))
    df = eng_fn(df)
    df["date"] = pd.to_datetime(df["date"]) if "date" in df.columns else pd.to_datetime(df.index)

    X_raw = df[feat_cols].values.astype(np.float32)
    X_scaled = scaler.transform(X_raw).astype(np.float32)

    seq_len = meta.get("seq_len", SEQ_LEN)
    X_seq, dates, prices, rets = [], [], [], []
    for i in range(seq_len, len(X_scaled)):
        X_seq.append(X_scaled[i - seq_len : i])
        dates.append(str(df["date"].iloc[i]) if "date" in df.columns else str(i))
        prices.append(float(df["close"].iloc[i]))
        rets.append(float(df["returns"].iloc[i]))
    X_seq = np.stack(X_seq)
    rets = np.array(rets)
    prices = np.array(prices)

    # 按 TEST_START 时间切分（冠军模型的训练已用此切分）
    test_start_ts = pd.Timestamp(TEST_START)
    seq_dates = pd.to_datetime(dates)
    test_mask = seq_dates >= test_start_ts
    n_test_by_date = int(test_mask.sum())

    if meta.get("is_champion") and n_test_by_date >= 100:
        # 冠军模型按日期严格切分
        first_test_idx = int(np.argmax(np.asarray(test_mask)))
        X_test = X_seq[first_test_idx:]
        rets_test = rets[first_test_idx:]
        prices_test = prices[first_test_idx:]
        dates_test = list(dates[first_test_idx:])
    else:
        # 旧基线模型按比例切分（保持原行为）
        n_test = int(len(X_seq) * test_ratio)
        if n_test < 30:
            return None
        X_test = X_seq[-n_test:]
        rets_test = rets[-n_test:]
        prices_test = prices[-n_test:]
        dates_test = dates[-n_test:]

    signal, prob_up = predict(model, meta, X_test)

    # 方向准确率
    actual_up = (rets_test > 0).astype(int)
    pred_up = (signal > 0).astype(int)
    direction_accuracy = float((actual_up == pred_up).mean())

    # 决定是否用冠军阈值
    if meta.get("is_champion") and prob_up is not None:
        tau = float(meta.get("threshold", 0.5))
        # signal = prob_up - 0.5，因此阈值应转成 (tau - 0.5)
        buy_thr = tau - 0.5
        sell_thr = 0.0
        conf_floor = CONFIDENCE_FLOOR
    else:
        buy_thr = 0.0
        sell_thr = 0.0
        conf_floor = None

    bt = run_backtest(
        signals=signal,
        prob_up=prob_up,
        returns=rets_test,
        prices=prices_test,
        dates=dates_test,
        buy_threshold=buy_thr,
        sell_threshold=sell_thr,
        confidence_floor=conf_floor,
        enforce_t_plus_1=True,
    )
    metrics = calculate_metrics(bt)
    metrics["direction_accuracy"] = direction_accuracy
    metrics["model_id"] = meta["model_id"] if meta.get("symbol") != "MULTI" else f"{meta['model_id']}_{symbol}"
    metrics["model_type"] = meta["model_type"]
    metrics["symbol"] = symbol

    # 存资金曲线
    peak = np.maximum.accumulate(bt["portfolio"])
    drawdown = ((bt["portfolio"] - peak) / peak).tolist()
    curve_data = {
        "model_id": metrics["model_id"],
        "symbol": symbol,
        "model_type": meta["model_type"],
        "is_champion": bool(meta.get("is_champion")),
        "threshold": meta.get("threshold"),
        "dates": [str(d) for d in dates_test],
        "portfolio_values": bt["portfolio"].tolist(),
        "benchmark_values": bt["benchmark"].tolist(),
        "daily_returns": bt["daily_returns"].tolist(),
        "drawdown": drawdown,
        "trades": bt["trades"],
    }
    (CURVES_DIR / f"{metrics['model_id']}.json").write_text(json.dumps(curve_data, ensure_ascii=False))
    return metrics


def backtest_single_model(model_dir: Path):
    model, scaler, meta = load_model(model_dir)
    sym = meta["symbol"]
    if sym == "MULTI":
        return [backtest_for_symbol(model, scaler, meta, s) for s in SYMBOLS_ALL]
    return backtest_for_symbol(model, scaler, meta, sym)


# =========================================================
# 聚合分析
# =========================================================

def analyze_results(results: list[dict]) -> dict:
    df = pd.DataFrame(results)

    # 冠军判定：必须有实际交易 ≥ 5 笔，Sharpe 作为最终排序
    # 优先选择有正超额收益的模型
    active = df[df["n_trades"] >= 5].copy()
    passive = df[df["n_trades"] < 5].copy()
    positive_excess = active[active["excess_return"] > 0].copy()

    df_sorted = df.sort_values("sharpe_ratio", ascending=False)
    if len(positive_excess) > 0:
        best = positive_excess.sort_values("sharpe_ratio", ascending=False).iloc[0]
    elif len(active) > 0:
        best = active.sort_values("sharpe_ratio", ascending=False).iloc[0]
    else:
        best = df_sorted.iloc[0]

    by_type = {}
    for mt, grp in df.groupby("model_type"):
        by_type[mt] = {
            "avg_sharpe": round(grp["sharpe_ratio"].mean(), 4),
            "avg_return": round(grp["total_return"].mean(), 4),
            "avg_direction_accuracy": round(grp["direction_accuracy"].mean(), 4),
            "avg_max_drawdown": round(grp["max_drawdown"].mean(), 4),
            "model_count": int(len(grp)),
        }

    advantages = []
    if best["sharpe_ratio"] > 1.5:
        advantages.append(f"高风险调整收益 (Sharpe {best['sharpe_ratio']:.2f})")
    if best["n_trades"] >= 30:
        advantages.append(f"活跃交易信号 ({int(best['n_trades'])} 笔交易)")
    if best["win_rate"] > 0.5:
        advantages.append(f"正胜率 ({best['win_rate']*100:.1f}%)")
    if best["excess_return"] > 0:
        advantages.append(f"正超额收益 (+{best['excess_return']*100:.1f}% vs 买入持有)")
    if best["direction_accuracy"] > 0.52:
        advantages.append(f"方向预测准确 ({best['direction_accuracy']*100:.1f}%)")

    why_best_map = {
        "transformer": (
            "Transformer 通过多头自注意力机制捕捉跨时间步的长程依赖。"
            "多股联合训练让模型学到可跨股票迁移的短期方向模式，"
            "结合学习到的决策阈值与置信度过滤，显著降低噪声交易，"
            "在低信噪比的 A 股市场取得稳健的风险调整收益。"
        ),
        "lightgbm": (
            "LightGBM 直接对滑窗展平后的特征做梯度提升树拟合，"
            "内置 L1/L2 正则与 feature/bagging subsampling，在小样本下不易过拟合，"
            "特征重要性可解释，MACD/RSI 贡献突出。"
        ),
        "xgboost": "XGBoost 与 LightGBM 同属梯度提升树，正则化更强但参数更敏感。",
        "lstm": "BiLSTM + Attention 通过双向时序建模与注意力加权捕捉关键时间点，"
                "对具有明显趋势的个股较友好。",
    }
    why_best = why_best_map.get(best["model_type"], "")

    return {
        "generated_at": datetime.now().isoformat(),
        "total_models": len(results),
        "active_trading_models": int(len(active)),
        "passive_models": int(len(passive)),
        "positive_excess_return_models": int(len(positive_excess)),
        "best_model": {
            "model_id": best["model_id"],
            "model_type": best["model_type"],
            "symbol": best["symbol"],
            "sharpe_ratio": round(float(best["sharpe_ratio"]), 4),
            "total_return": round(float(best["total_return"]), 4),
            "annual_return": round(float(best["annual_return"]), 4),
            "max_drawdown": round(float(best["max_drawdown"]), 4),
            "direction_accuracy": round(float(best["direction_accuracy"]), 4),
            "win_rate": round(float(best["win_rate"]), 4),
            "n_trades": int(best["n_trades"]),
            "excess_return": round(float(best["excess_return"]), 4),
            "advantages": advantages,
            "why_best": why_best,
        },
        "by_model_type": by_type,
        "rankings": df_sorted[
            ["model_id", "model_type", "symbol", "sharpe_ratio",
             "total_return", "max_drawdown", "direction_accuracy",
             "n_trades", "excess_return"]
        ].round(4).to_dict("records"),
    }


# =========================================================
# 主流程
# =========================================================

def run_all_models():
    print("=" * 70)
    print("DLQI Pipeline: 全模型回测 + 冠军分析")
    print(f"A 股约束: T+1 · 买成本 {COST_BUY*100:.3f}% · 卖成本 {COST_SELL*100:.3f}% · max_hold {MAX_HOLD_DAYS} 天")
    print("=" * 70)

    model_dirs = sorted(
        [d for d in MODELS_DIR.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
    )
    print(f"\n找到 {len(model_dirs)} 个模型\n")

    results = []
    for i, md in enumerate(model_dirs, 1):
        name = md.name
        print(f"[{i:2d}/{len(model_dirs)}] {name} ... ", end="", flush=True)
        try:
            r = backtest_single_model(md)
            if r is None:
                print("SKIP (no data)")
                continue
            if isinstance(r, list):
                per_sym = [x for x in r if x is not None]
                for m in per_sym:
                    results.append(m)
                    print(f"\n      {m['symbol']}: Sharpe={m['sharpe_ratio']:.3f}"
                          f" Trades={m['n_trades']} DirAcc={m['direction_accuracy']:.1%}"
                          f" Excess={m['excess_return']:+.1%}", end="")
                print()
            else:
                results.append(r)
                print(f"Sharpe={r['sharpe_ratio']:.3f} Trades={r['n_trades']}"
                      f" DirAcc={r['direction_accuracy']:.1%} Excess={r['excess_return']:+.1%}")
        except Exception as e:
            print(f"ERROR: {e}")

    if not results:
        print("\n没有回测结果！")
        return

    df = pd.DataFrame(results)
    cols = ["total_return", "annual_return", "volatility", "max_drawdown",
            "sharpe_ratio", "sortino_ratio", "calmar_ratio", "direction_accuracy",
            "win_rate", "profit_factor", "n_trades", "total_commission",
            "symbol", "model_type", "model_id", "benchmark_return", "excess_return"]
    df[cols].to_csv(RESULTS_DIR / "backtest_results.csv", index=False)
    print(f"\n保存: results/backtest_results.csv")

    analysis = analyze_results(results)
    (RESULTS_DIR / "model_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2)
    )
    print("保存: results/model_analysis.json")

    # 打印排名
    print("\n" + "=" * 90)
    print("模型性能排名 (按 Sharpe Ratio)")
    print("=" * 90)
    print(f"{'Rank':<5}{'Model':<47}{'Sharpe':>8}{'Return':>9}{'MaxDD':>9}{'DirAcc':>8}{'Trades':>7}{'Excess':>9}")
    print("-" * 102)
    for idx, r in enumerate(analysis["rankings"], 1):
        marker = " ★" if r["model_id"] == analysis["best_model"]["model_id"] else ""
        print(f"{idx:<5}{r['model_id'][:45]:<47}"
              f"{r['sharpe_ratio']:>8.3f}{r['total_return']:>8.1%}{r['max_drawdown']:>8.1%}"
              f"{r['direction_accuracy']:>7.1%}{r['n_trades']:>7}{r['excess_return']:>+8.1%}{marker}")

    best = analysis["best_model"]
    print(f"\n{'=' * 90}\n★ 最佳主策略: {best['model_type'].upper()} - {best['symbol']} ({best['model_id']})")
    print(f"   Sharpe={best['sharpe_ratio']:.3f}  年化={best['annual_return']:.1%}"
          f"  MaxDD={best['max_drawdown']:.1%}  方向准确率={best['direction_accuracy']:.1%}"
          f"  胜率={best['win_rate']:.1%}  交易={best['n_trades']}  超额={best['excess_return']:+.1%}")
    for a in best["advantages"]:
        print(f"   ✓ {a}")


# =========================================================
# 消融实验（冠军专属）
# =========================================================

def _latest_champion_dir() -> Path | None:
    candidates = sorted(MODELS_DIR.glob("transformer_MULTI_*"), reverse=True)
    return candidates[0] if candidates else None


def run_ablation():
    """对最新的冠军模型跑 4 个回测变体。"""
    champ_dir = _latest_champion_dir()
    if not champ_dir:
        print("未找到冠军模型，请先跑 scripts/train_champion.py")
        return

    print("=" * 70)
    print(f"冠军消融实验: {champ_dir.name}")
    print("=" * 70)

    model, scaler, meta = load_model(champ_dir)
    tau = float(meta.get("threshold", 0.5))

    variants = [
        {
            "name": "baseline (τ=0.5, 无置信度过滤, T+0, 对称费率)",
            "buy_thr": 0.0, "sell_thr": 0.0, "confidence": None,
            "t1": False, "cost_buy": 0.0015, "cost_sell": 0.0015,
        },
        {
            "name": "+ 决策阈值 τ*",
            "buy_thr": tau - 0.5, "sell_thr": 0.0, "confidence": None,
            "t1": False, "cost_buy": 0.0015, "cost_sell": 0.0015,
        },
        {
            "name": "+ 阈值 + 置信度过滤 0.55",
            "buy_thr": tau - 0.5, "sell_thr": 0.0, "confidence": CONFIDENCE_FLOOR,
            "t1": False, "cost_buy": 0.0015, "cost_sell": 0.0015,
        },
        {
            "name": "+ 阈值 + 置信度 + T+1 + 非对称费率 (最终冠军)",
            "buy_thr": tau - 0.5, "sell_thr": 0.0, "confidence": CONFIDENCE_FLOOR,
            "t1": True, "cost_buy": COST_BUY, "cost_sell": COST_SELL,
        },
    ]

    all_rows = []
    for v in variants:
        print(f"\n▶ {v['name']}")
        agg_trades = 0
        per_sym_rows = []
        for sym in SYMBOLS_ALL:
            bt_metrics = _ablation_one(model, scaler, meta, sym, v)
            if bt_metrics is None:
                continue
            agg_trades += bt_metrics["n_trades"]
            per_sym_rows.append(bt_metrics)
            print(f"  {sym}: Sharpe={bt_metrics['sharpe_ratio']:.3f}"
                  f" Return={bt_metrics['total_return']:+.1%}"
                  f" Excess={bt_metrics['excess_return']:+.1%}"
                  f" Trades={bt_metrics['n_trades']}")

        # 汇总一行：按权重均值（简单平均）
        if per_sym_rows:
            row = {
                "variant": v["name"],
                "avg_sharpe": round(np.mean([r["sharpe_ratio"] for r in per_sym_rows]), 4),
                "avg_return": round(np.mean([r["total_return"] for r in per_sym_rows]), 4),
                "avg_excess": round(np.mean([r["excess_return"] for r in per_sym_rows]), 4),
                "avg_max_drawdown": round(np.mean([r["max_drawdown"] for r in per_sym_rows]), 4),
                "avg_direction_accuracy": round(np.mean([r["direction_accuracy"] for r in per_sym_rows]), 4),
                "avg_win_rate": round(np.mean([r["win_rate"] for r in per_sym_rows]), 4),
                "total_trades": int(sum(r["n_trades"] for r in per_sym_rows)),
            }
            all_rows.append(row)

    out_csv = RESULTS_DIR / "ablation.csv"
    pd.DataFrame(all_rows).to_csv(out_csv, index=False)
    print(f"\n消融实验结果: {out_csv}")
    print("\n" + "=" * 100)
    print(f"{'变体':<55}{'AvgSharpe':>11}{'AvgRet':>10}{'AvgExc':>10}{'AvgDD':>10}{'Trades':>8}")
    print("-" * 100)
    for r in all_rows:
        print(f"{r['variant'][:53]:<55}{r['avg_sharpe']:>11.3f}"
              f"{r['avg_return']:>9.1%}{r['avg_excess']:>+9.1%}"
              f"{r['avg_max_drawdown']:>9.1%}{r['total_trades']:>8}")


def _ablation_one(model, scaler, meta: dict, symbol: str, v: dict) -> dict | None:
    csv = RAW_DIR / f"cn_{symbol}.csv"
    if not csv.exists():
        return None
    df = pd.read_csv(csv)
    df = engineer_features_v2(df)
    X_raw = df[FEATURE_COLS_V2].values.astype(np.float32)
    X_scaled = scaler.transform(X_raw).astype(np.float32)

    X_seq, dates, prices, rets = [], [], [], []
    for i in range(SEQ_LEN, len(X_scaled)):
        X_seq.append(X_scaled[i - SEQ_LEN : i])
        dates.append(str(df["date"].iloc[i]))
        prices.append(float(df["close"].iloc[i]))
        rets.append(float(df["returns"].iloc[i]))
    X_seq = np.stack(X_seq)
    rets = np.array(rets)
    prices = np.array(prices)

    n_test = int(len(X_seq) * 0.15)
    if n_test < 30:
        return None
    X_test = X_seq[-n_test:]
    rets_t = rets[-n_test:]
    prices_t = prices[-n_test:]
    dates_t = dates[-n_test:]

    signal, prob_up = predict(model, meta, X_test)
    actual_up = (rets_t > 0).astype(int)
    pred_up = (signal > 0).astype(int)
    da = float((actual_up == pred_up).mean())

    bt = run_backtest(
        signals=signal,
        prob_up=prob_up,
        returns=rets_t,
        prices=prices_t,
        dates=dates_t,
        buy_threshold=v["buy_thr"],
        sell_threshold=v["sell_thr"],
        confidence_floor=v["confidence"],
        enforce_t_plus_1=v["t1"],
        cost_buy=v["cost_buy"],
        cost_sell=v["cost_sell"],
    )
    m = calculate_metrics(bt)
    m["direction_accuracy"] = da
    m["symbol"] = symbol
    return m


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ablation", action="store_true", help="对最新冠军跑消融实验")
    args = parser.parse_args()
    if args.ablation:
        run_ablation()
    else:
        run_all_models()
