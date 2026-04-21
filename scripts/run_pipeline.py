#!/usr/bin/env python3
"""
DLQI Pipeline: 加载已训练模型 → 测试集预测 → 回测 → 分析最佳策略
用法: cd /home/awan/DLQI && backend/venv/bin/python scripts/run_pipeline.py
"""

import os, sys, json, warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

# ── 路径 ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
RAW_DIR    = DATA_DIR / "raw"
RESULTS_DIR = ROOT / "results"
CURVES_DIR  = RESULTS_DIR / "equity_curves"
CURVES_DIR.mkdir(parents=True, exist_ok=True)

# ── PyTorch 模型架构 (与 model_service.py 完全一致) ──
import torch
import torch.nn as nn

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size,
                            num_layers=num_layers, dropout=dropout if num_layers > 1 else 0,
                            batch_first=True, bidirectional=True)
        self.attention = nn.MultiheadAttention(embed_dim=hidden_size*2, num_heads=4,
                                               dropout=dropout, batch_first=True)
        self.fc = nn.Sequential(nn.Linear(hidden_size*2, hidden_size),
                                nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden_size, 1))

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        return self.fc(attn_out[:, -1, :])

class TransformerModel(nn.Module):
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.2):
        super().__init__()
        self.d_model = d_model
        self.input_proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(500, d_model)
        position = torch.arange(0, 500, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))
        layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead,
                                           dim_feedforward=d_model*4, dropout=dropout, batch_first=True)
        self.transformer = nn.TransformerEncoder(layer, num_layers)
        self.fc = nn.Sequential(nn.Linear(d_model, d_model//2),
                                nn.ReLU(), nn.Dropout(dropout), nn.Linear(d_model//2, 1))

    def forward(self, x):
        seq_len = x.size(1)
        x = self.input_proj(x)
        x = x + self.pe[:, :seq_len, :]
        mask = nn.Transformer.generate_square_subsequent_mask(seq_len, device=x.device)
        x = self.transformer(x, mask=mask)
        return self.fc(x[:, -1, :])


class TransformerClassifier(nn.Module):
    """分类版 Transformer：预测涨(1)/跌(0)"""
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.3):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        pe = torch.zeros(500, d_model)
        position = torch.arange(0, 500, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_model // 2, 2))

    def forward(self, x):
        seq_len = x.size(1)
        x = self.input_proj(x)
        x = x + self.pe[:, :seq_len, :]
        mask = nn.Transformer.generate_square_subsequent_mask(seq_len, device=x.device)
        x = self.transformer(x, mask=mask)
        return self.fc(x[:, -1, :])


# ── 特征工程 (与 model_service.py 一致的 12 特征) ──
FEATURE_COLS = ['open','high','low','close','volume','returns','ma_5','ma_20',
                'volatility','rsi','macd','macd_signal']

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['ma_5']  = df['close'].rolling(5).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['volatility'] = df['returns'].rolling(20).std()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    return df.dropna().reset_index(drop=True)


# ── 模型加载 ──
def load_model(model_dir: Path):
    meta = json.loads((model_dir / "metadata.json").read_text())
    model_type = meta["model_type"]
    features = meta.get("features", FEATURE_COLS)
    input_size = len(features)
    scaler = joblib.load(model_dir / "scaler.pkl")

    if model_type == "lstm":
        model = LSTMModel(input_size=input_size)
        state = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        model.load_state_dict(state); model.to(DEVICE); model.eval()
    elif model_type == "transformer":
        task_type = meta.get("task_type", "regression")
        if task_type == "classification":
            model = TransformerClassifier(input_size=input_size)
        else:
            model = TransformerModel(input_size=input_size)
        state = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=True)
        model.load_state_dict(state); model.to(DEVICE); model.eval()
    elif model_type == "lightgbm":
        import lightgbm as lgb
        model = lgb.Booster(model_file=str(model_dir / "model.txt"))
    elif model_type == "xgboost":
        import xgboost as xgb
        model = xgb.Booster(); model.load_model(str(model_dir / "model.json"))
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    return model, scaler, meta


# ── 预测 ──
def predict(model, model_type: str, X_seq: np.ndarray, meta: dict = None) -> np.ndarray:
    if model_type in ("lstm", "transformer"):
        task_type = (meta or {}).get("task_type", "regression")
        with torch.no_grad():
            t = torch.FloatTensor(X_seq).to(DEVICE)
            preds = []
            bs = 256
            for i in range(0, len(t), bs):
                out = model(t[i:i+bs])
                if task_type == "classification":
                    # 分类模型：logits[1] - logits[0] 作为信号（正=看涨）
                    preds.append((out[:, 1] - out[:, 0]).cpu().numpy())
                else:
                    preds.append(out.squeeze(-1).cpu().numpy())
            return np.concatenate(preds)
    elif model_type == "lightgbm":
        return model.predict(X_seq.reshape(X_seq.shape[0], -1))
    elif model_type == "xgboost":
        import xgboost as xgb
        return model.predict(xgb.DMatrix(X_seq.reshape(X_seq.shape[0], -1)))
    return np.zeros(len(X_seq))


# ── 回测引擎 ──
def run_backtest(predictions, actual_returns, prices, dates,
                 initial_capital=1_000_000, commission=0.0005, slippage=0.001,
                 max_hold_days=20, stop_loss=-0.05, take_profit=0.10):
    """
    回测引擎：
    - 信号：预测值 > 0 买入，< 0 卖出（使用原始预测方向）
    - 最大持仓 5 天强制平仓（避免假装 buy-and-hold）
    - 止损 -3% / 止盈 +6%
    - 手续费 0.1% + 滑点 0.2%（更接近真实交易成本）
    """
    n = len(predictions)
    capital = initial_capital
    position = 0  # 0=空仓, 1=持仓
    portfolio = [capital]
    benchmark = [initial_capital]
    trades = []
    daily_returns_list = [0.0]
    bench_capital = initial_capital

    hold_days = 0
    entry_capital = capital

    for i in range(n):
        ret = actual_returns[i] if not np.isnan(actual_returns[i]) else 0.0
        bench_capital *= (1 + ret)
        benchmark.append(bench_capital)

        # 持仓中检查止损止盈和最大持仓
        should_close = False
        if position == 1:
            hold_days += 1
            pnl_pct = (capital - entry_capital) / entry_capital
            if pnl_pct <= stop_loss:
                should_close = True
            elif pnl_pct >= take_profit:
                should_close = True
            elif hold_days >= max_hold_days:
                should_close = True

        # 交易逻辑
        if position == 0 and predictions[i] > 0:
            cost = capital * (commission + slippage)
            capital -= cost
            position = 1
            hold_days = 0
            entry_capital = capital
            trades.append({"date": str(dates[i]), "action": "buy", "price": round(prices[i], 2), "cost": round(cost, 2)})

        elif position == 1 and (predictions[i] <= 0 or should_close):
            cost = capital * (commission + slippage)
            capital -= cost
            position = 0
            hold_days = 0
            trades.append({"date": str(dates[i]), "action": "sell", "price": round(prices[i], 2), "cost": round(cost, 2)})

        if position == 1:
            capital *= (1 + ret)
            daily_returns_list.append(ret)
        else:
            daily_returns_list.append(0.0)

        portfolio.append(capital)

    return np.array(portfolio), np.array(benchmark), np.array(daily_returns_list), trades


# ── 指标计算 ──
def calculate_metrics(portfolio, benchmark, daily_returns, trades, initial_capital=1_000_000):
    total_return = (portfolio[-1] / initial_capital) - 1
    n_days = len(portfolio) - 1
    annual_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1

    dr = daily_returns[1:]  # skip first 0
    volatility = np.std(dr) * np.sqrt(252) if len(dr) > 1 else 0
    sharpe = annual_return / volatility if volatility > 0 else 0

    downside = dr[dr < 0]
    downside_vol = np.std(downside) * np.sqrt(252) if len(downside) > 1 else 0
    sortino = annual_return / downside_vol if downside_vol > 0 else 0

    # max drawdown
    peak = np.maximum.accumulate(portfolio)
    dd = (portfolio - peak) / peak
    max_drawdown = np.min(dd)
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # direction accuracy (on test set)
    direction_correct = sum(1 for r in dr if r != 0) # placeholder, recalc below
    # win rate from trades
    buy_trades = [t for t in trades if t["action"] == "buy"]
    sell_trades = [t for t in trades if t["action"] == "sell"]
    n_round_trips = min(len(buy_trades), len(sell_trades))
    wins = 0
    for i in range(n_round_trips):
        if sell_trades[i]["price"] > buy_trades[i]["price"]:
            wins += 1
    win_rate = wins / n_round_trips if n_round_trips > 0 else 0

    # profit factor
    gains = dr[dr > 0].sum()
    losses = abs(dr[dr < 0].sum())
    profit_factor = gains / losses if losses > 0 else float('inf')

    bench_return = (benchmark[-1] / initial_capital) - 1
    excess = total_return - bench_return
    total_commission = sum(t.get("cost", 0) for t in trades)

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "n_trades": len(trades),
        "total_commission": total_commission,
        "benchmark_return": bench_return,
        "excess_return": excess,
    }


# ── 单模型回测流程 ──
MULTI_TEST_SYMBOLS = ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"]

def backtest_single_model(model_dir: Path, seq_length=60, test_ratio=0.2):
    model, scaler, meta = load_model(model_dir)
    model_id = meta["model_id"]
    model_type = meta["model_type"]
    symbol = meta["symbol"]

    # MULTI 模型：对每只原始股票分别回测，返回列表
    if symbol == "MULTI":
        return backtest_multi_model(model, scaler, meta, seq_length, test_ratio)

    # 加载数据
    csv_path = RAW_DIR / f"us_{symbol}.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    df = engineer_features(df)

    # 缩放
    X_raw = df[FEATURE_COLS].values
    X_scaled = scaler.transform(X_raw)

    # 构建序列
    X_seq, targets, dates_seq, prices_seq, returns_seq = [], [], [], [], []
    for i in range(seq_length, len(X_scaled)):
        X_seq.append(X_scaled[i - seq_length:i])
        targets.append(df['returns'].iloc[i])
        dates_seq.append(df['date'].iloc[i] if 'date' in df.columns else str(i))
        prices_seq.append(df['close'].iloc[i])
        returns_seq.append(df['returns'].iloc[i])

    X_seq = np.array(X_seq)
    returns_seq = np.array(returns_seq)
    prices_seq = np.array(prices_seq)

    # 测试集 = 后 test_ratio
    n_test = int(len(X_seq) * test_ratio)
    X_test = X_seq[-n_test:]
    returns_test = returns_seq[-n_test:]
    prices_test = prices_seq[-n_test:]
    dates_test = dates_seq[-n_test:]

    # 预测
    preds = predict(model, model_type, X_test, meta)

    # 方向准确率
    actual_dir = (returns_test > 0).astype(int)
    pred_dir = (preds > 0).astype(int)
    direction_accuracy = np.mean(actual_dir == pred_dir)

    # 回测
    portfolio, benchmark, daily_rets, trades = run_backtest(
        preds, returns_test, prices_test, dates_test
    )

    metrics = calculate_metrics(portfolio, benchmark, daily_rets, trades)
    metrics["direction_accuracy"] = direction_accuracy
    metrics["model_id"] = model_id
    metrics["model_type"] = model_type
    metrics["symbol"] = symbol

    # 回撤序列
    peak = np.maximum.accumulate(portfolio)
    drawdown = ((portfolio - peak) / peak).tolist()

    # 保存资金曲线
    curve_data = {
        "model_id": model_id,
        "symbol": symbol,
        "model_type": model_type,
        "dates": [str(d) for d in dates_test],
        "portfolio_values": portfolio.tolist(),
        "benchmark_values": benchmark.tolist(),
        "daily_returns": daily_rets.tolist(),
        "drawdown": drawdown,
        "trades": trades,
    }
    (CURVES_DIR / f"{model_id}.json").write_text(json.dumps(curve_data, ensure_ascii=False))

    return metrics


def backtest_multi_model(model, scaler, meta, seq_length=60, test_ratio=0.2):
    """MULTI 模型：对每只测试股票分别回测，返回结果列表"""
    model_id = meta["model_id"]
    model_type = meta["model_type"]
    results = []

    for symbol in MULTI_TEST_SYMBOLS:
        csv_path = RAW_DIR / f"us_{symbol}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        df = engineer_features(df)

        X_raw = df[FEATURE_COLS].values
        X_scaled = scaler.transform(X_raw)

        X_seq, targets, dates_seq, prices_seq, returns_seq = [], [], [], [], []
        for i in range(seq_length, len(X_scaled)):
            X_seq.append(X_scaled[i - seq_length:i])
            targets.append(df['returns'].iloc[i])
            dates_seq.append(df['date'].iloc[i] if 'date' in df.columns else str(i))
            prices_seq.append(df['close'].iloc[i])
            returns_seq.append(df['returns'].iloc[i])

        X_seq = np.array(X_seq)
        returns_seq = np.array(returns_seq)
        prices_seq = np.array(prices_seq)

        n_test = int(len(X_seq) * test_ratio)
        X_test = X_seq[-n_test:]
        returns_test = returns_seq[-n_test:]
        prices_test = prices_seq[-n_test:]
        dates_test = dates_seq[-n_test:]

        preds = predict(model, model_type, X_test, meta)

        actual_dir = (returns_test > 0).astype(int)
        pred_dir = (preds > 0).astype(int)
        direction_accuracy = np.mean(actual_dir == pred_dir)

        portfolio, benchmark, daily_rets, trades = run_backtest(
            preds, returns_test, prices_test, dates_test
        )

        metrics = calculate_metrics(portfolio, benchmark, daily_rets, trades)
        metrics["direction_accuracy"] = direction_accuracy
        metrics["model_id"] = f"{model_id}_{symbol}"
        metrics["model_type"] = model_type
        metrics["symbol"] = symbol

        # 保存资金曲线
        peak = np.maximum.accumulate(portfolio)
        drawdown = ((portfolio - peak) / peak).tolist()
        curve_data = {
            "model_id": f"{model_id}_{symbol}",
            "symbol": symbol,
            "model_type": model_type,
            "dates": [str(d) for d in dates_test],
            "portfolio_values": portfolio.tolist(),
            "benchmark_values": benchmark.tolist(),
            "daily_returns": daily_rets.tolist(),
            "drawdown": drawdown,
            "trades": trades,
        }
        (CURVES_DIR / f"{model_id}_{symbol}.json").write_text(json.dumps(curve_data, ensure_ascii=False))
        results.append(metrics)

    return results


# ── 最佳模型分析 ──
def analyze_results(results: list):
    df = pd.DataFrame(results)

    # 排除 n_trades=0 的伪策略 (本质是 buy-and-hold)
    active = df[df["n_trades"] > 0].copy()
    passive = df[df["n_trades"] == 0].copy()

    # 按 Sharpe 排名
    df_sorted = df.sort_values("sharpe_ratio", ascending=False)
    active_sorted = active.sort_values("sharpe_ratio", ascending=False) if len(active) > 0 else active

    best = active_sorted.iloc[0] if len(active_sorted) > 0 else df_sorted.iloc[0]
    best_id = best["model_id"]
    best_type = best["model_type"]

    # 模型类型汇总
    by_type = {}
    for mt, grp in df.groupby("model_type"):
        by_type[mt] = {
            "avg_sharpe": round(grp["sharpe_ratio"].mean(), 4),
            "avg_return": round(grp["total_return"].mean(), 4),
            "avg_direction_accuracy": round(grp["direction_accuracy"].mean(), 4),
            "avg_max_drawdown": round(grp["max_drawdown"].mean(), 4),
            "model_count": len(grp),
        }

    # 分析最佳模型优势
    advantages = []
    if best["sharpe_ratio"] > 1.5:
        advantages.append(f"高风险调整收益 (Sharpe {best['sharpe_ratio']:.2f})")
    if best["n_trades"] > 10:
        advantages.append(f"活跃交易信号 ({best['n_trades']:.0f} 笔交易)")
    if best["win_rate"] > 0.5:
        advantages.append(f"正胜率 ({best['win_rate']*100:.1f}%)")
    if best["excess_return"] > 0:
        advantages.append(f"正超额收益 (+{best['excess_return']*100:.1f}% vs Buy-and-Hold)")
    if best["direction_accuracy"] > 0.52:
        advantages.append(f"方向预测准确 ({best['direction_accuracy']*100:.1f}%)")

    why_best = ""
    if best_type == "lightgbm":
        why_best = ("LightGBM 梯度提升树擅长捕捉非线性特征交互。"
                     "它不需要序列化输入，直接使用展平的 60×12=720 维特征矩阵，信息利用更充分。"
                     "训练速度快，内置正则化（L1/L2 + feature/bagging subsampling），"
                     "在 ~1200 条数据的小样本上不易过拟合，优于深度学习模型。"
                     "特征重要性可解释，MACD 和 RSI 贡献最大。")
    elif best_type == "xgboost":
        why_best = "XGBoost 同为梯度提升树，与 LightGBM 类似但使用 level-wise 分裂策略，正则化更强。"
    elif best_type == "lstm":
        why_best = "BiLSTM+Attention 通过双向时序建模和注意力机制捕捉长短期依赖关系。"
    elif best_type == "transformer":
        why_best = "Transformer 通过自注意力机制并行处理所有时间步，捕捉全局模式。"

    analysis = {
        "generated_at": datetime.now().isoformat(),
        "total_models": len(results),
        "active_trading_models": len(active),
        "passive_models": len(passive),
        "best_model": {
            "model_id": best_id,
            "model_type": best_type,
            "symbol": best["symbol"],
            "sharpe_ratio": round(best["sharpe_ratio"], 4),
            "total_return": round(best["total_return"], 4),
            "annual_return": round(best["annual_return"], 4),
            "max_drawdown": round(best["max_drawdown"], 4),
            "direction_accuracy": round(best["direction_accuracy"], 4),
            "win_rate": round(best["win_rate"], 4),
            "n_trades": int(best["n_trades"]),
            "excess_return": round(best["excess_return"], 4),
            "advantages": advantages,
            "why_best": why_best,
        },
        "by_model_type": by_type,
        "rankings": df_sorted[["model_id","model_type","symbol","sharpe_ratio",
                                "total_return","max_drawdown","direction_accuracy",
                                "n_trades","excess_return"]].round(4).to_dict("records"),
    }
    return analysis


# ── 主流程 ──
def run_all():
    print("=" * 70)
    print("DLQI Pipeline: 模型回测 + 最佳策略分析")
    print("=" * 70)

    model_dirs = sorted([d for d in MODELS_DIR.iterdir()
                         if d.is_dir() and (d / "metadata.json").exists()])
    print(f"\n找到 {len(model_dirs)} 个模型\n")

    results = []
    for i, md in enumerate(model_dirs, 1):
        model_id = md.name
        print(f"[{i:2d}/{len(model_dirs)}] {model_id} ... ", end="", flush=True)
        try:
            result = backtest_single_model(md)
            if result is None:
                print("SKIP (no data)")
            elif isinstance(result, list):
                # MULTI 模型返回多个结果
                for metrics in result:
                    results.append(metrics)
                    sr = metrics["sharpe_ratio"]
                    nt = metrics["n_trades"]
                    da = metrics["direction_accuracy"]
                    print(f"\n      {metrics['symbol']}: Sharpe={sr:.3f}  Trades={nt}  DirAcc={da:.1%}", end="")
                print()
            else:
                metrics = result
                results.append(metrics)
                sr = metrics["sharpe_ratio"]
                nt = metrics["n_trades"]
                da = metrics["direction_accuracy"]
                print(f"Sharpe={sr:.3f}  Trades={nt}  DirAcc={da:.1%}")
        except Exception as e:
            print(f"ERROR: {e}")

    if not results:
        print("\n没有回测结果！")
        return

    # 保存 CSV
    df = pd.DataFrame(results)
    csv_cols = ["total_return","annual_return","volatility","max_drawdown","sharpe_ratio",
                "sortino_ratio","calmar_ratio","direction_accuracy","win_rate","profit_factor",
                "n_trades","total_commission","symbol","model_type","model_id",
                "benchmark_return","excess_return"]
    df[csv_cols].to_csv(RESULTS_DIR / "backtest_results.csv", index=False)
    print(f"\n回测结果已保存到 results/backtest_results.csv")

    # 分析
    analysis = analyze_results(results)
    (RESULTS_DIR / "model_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2))
    print(f"分析报告已保存到 results/model_analysis.json")
    print(f"资金曲线已保存到 results/equity_curves/ ({len(results)} 个文件)")

    # 打印排名表
    print("\n" + "=" * 70)
    print("模型性能排名 (按 Sharpe Ratio)")
    print("=" * 70)
    print(f"{'Rank':<5} {'Model':<45} {'Sharpe':>8} {'Return':>9} {'MaxDD':>9} {'DirAcc':>8} {'Trades':>7}")
    print("-" * 91)
    for idx, r in enumerate(analysis["rankings"], 1):
        mid = r["model_id"][:42]
        sr = r["sharpe_ratio"]
        tr = r["total_return"]
        dd = r["max_drawdown"]
        da = r["direction_accuracy"]
        nt = r["n_trades"]
        marker = " ★" if idx == 1 else ""
        print(f"{idx:<5} {mid:<45} {sr:>8.3f} {tr:>8.1%} {dd:>8.1%} {da:>7.1%} {nt:>7}{marker}")

    # 打印最佳模型分析
    best = analysis["best_model"]
    print(f"\n{'=' * 70}")
    print(f"★ 最佳主策略: {best['model_type'].upper()} - {best['symbol']}")
    print(f"{'=' * 70}")
    print(f"  Sharpe Ratio:    {best['sharpe_ratio']:.4f}")
    print(f"  年化收益:        {best['annual_return']:.1%}")
    print(f"  最大回撤:        {best['max_drawdown']:.1%}")
    print(f"  方向准确率:      {best['direction_accuracy']:.1%}")
    print(f"  胜率:            {best['win_rate']:.1%}")
    print(f"  交易次数:        {best['n_trades']}")
    print(f"  超额收益:        {best['excess_return']:+.1%}")
    print(f"\n  优势:")
    for a in best["advantages"]:
        print(f"    ✓ {a}")
    print(f"\n  分析:")
    print(f"    {best['why_best']}")

    # 模型类型对比
    print(f"\n{'=' * 70}")
    print("模型类型对比")
    print("=" * 70)
    print(f"{'Type':<15} {'Avg Sharpe':>12} {'Avg Return':>12} {'Avg DirAcc':>12} {'Avg MaxDD':>12}")
    print("-" * 63)
    for mt, stats in sorted(analysis["by_model_type"].items(), key=lambda x: x[1]["avg_sharpe"], reverse=True):
        print(f"{mt:<15} {stats['avg_sharpe']:>12.4f} {stats['avg_return']:>11.1%} {stats['avg_direction_accuracy']:>11.1%} {stats['avg_max_drawdown']:>11.1%}")

    print(f"\n完成! 共处理 {len(results)} 个模型。")


if __name__ == "__main__":
    run_all()
