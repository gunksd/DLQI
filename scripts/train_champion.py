#!/usr/bin/env python3
"""
DLQI 主模型训练 — 多股联合 Transformer 分类器

与 scripts/train_cn_models.py 中的 transformer_MULTI 的关键差异：
  1. 24 维特征（scripts/common_features.FEATURE_COLS_V2）
  2. 时序安全切分：每股先按时间切 70/15/15，再在训练集内跨股 shuffle
  3. 扩大容量：d_model=128, 8 heads, 3 layers
  4. Warmup (线性) + cosine decay 学习率
  5. 在验证集上学习最优决策阈值 τ*（最大化 F1），保存到 metadata
  6. 小规模超参搜索（学习率 × dropout），保留验证集 F1 最高的一组

用法：
  cd /home/awan/DLQI && backend/venv/bin/python scripts/train_transformer.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from common_features import FEATURE_COLS_V2, engineer_features_v2  # noqa: E402

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MODELS_DIR = DATA_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SYMBOLS = ["600519", "601318", "600036", "300750", "002594"]
SEQ_LEN = 60
# 按时间切分（覆盖 2016-2026 完整十年周期）
TRAIN_END = "2019-12-31"   # 训练：2016-2019（约4年）
VAL_END   = "2020-12-31"   # 验证：2020 全年
# 测试：2021-01-01 起所有数据（约5年，含2021牛尾、2022熊市、2023-2025震荡）

BATCH_SIZE = 256
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


# =========================================================
# 模型
# =========================================================

class TransformerModel(nn.Module):
    """多股联合 Transformer 分类器。输出 shape = (B, 2) logits。"""

    def __init__(
        self,
        input_size: int,
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 3,
        dropout: float = 0.3,
        seq_len: int = SEQ_LEN,
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)

        pe = torch.zeros(seq_len, d_model)
        position = torch.arange(0, seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = x + self.pe[:, : x.size(1), :]
        mask = nn.Transformer.generate_square_subsequent_mask(x.size(1), device=x.device)
        x = self.transformer(x, mask=mask)
        x = self.norm(x[:, -1, :])
        return self.head(x)


# =========================================================
# 数据准备
# =========================================================

@dataclass
class SplitArrays:
    X_train: np.ndarray
    y_train: np.ndarray  # 分类标签 {0,1}
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    test_returns: np.ndarray  # 用于后续回测（可选）


def build_per_stock_arrays(symbol: str, scaler: StandardScaler | None) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """读取单只股票 → 特征工程 → 滑动窗口 → (X_seq, y_return, y_cls, full_df)。
    只负责构建序列，不切分。"""
    csv = RAW_DIR / f"cn_{symbol}.csv"
    df = pd.read_csv(csv)
    df = engineer_features_v2(df)

    X_raw = df[FEATURE_COLS_V2].values.astype(np.float32)
    returns = df["returns"].values.astype(np.float32)

    if scaler is None:
        raise ValueError("scaler must be fitted on training data first")
    X_scaled = scaler.transform(X_raw).astype(np.float32)

    X_seq = np.stack([X_scaled[i - SEQ_LEN : i] for i in range(SEQ_LEN, len(X_scaled))])
    # 目标：下一日是否上涨（预测 i 的 returns，用 seq [i-SEQ_LEN:i] 来预测）
    y_return = returns[SEQ_LEN:]
    y_cls = (y_return > 0).astype(np.int64)
    return X_seq, y_return, y_cls, df


def prepare_dataset() -> tuple[SplitArrays, StandardScaler, dict]:
    """按股票先时序切（按日期 TRAIN_END/VAL_END），再跨股 concat；scaler 仅用训练片段拟合。"""
    per_stock_splits = {}
    train_raw_features = []
    meta = {"per_stock_counts": {}, "feature_cols": FEATURE_COLS_V2}

    train_end = pd.Timestamp(TRAIN_END)
    val_end   = pd.Timestamp(VAL_END)

    # Step 1: 按股票切分原始特征，只拿训练段拟合 scaler
    for sym in SYMBOLS:
        csv = RAW_DIR / f"cn_{sym}.csv"
        df = pd.read_csv(csv)
        df = engineer_features_v2(df)
        df["date"] = pd.to_datetime(df["date"])

        n = len(df)
        # 按日期定位切分点
        n_train = int((df["date"] <= train_end).sum())
        n_val_end = int((df["date"] <= val_end).sum())
        n_val = n_val_end - n_train  # 验证集长度
        train_feats = df[FEATURE_COLS_V2].iloc[:n_train].values.astype(np.float32)
        train_raw_features.append(train_feats)

        per_stock_splits[sym] = {"df": df, "n": n, "n_train": n_train, "n_val": n_val}

    all_train_raw = np.concatenate(train_raw_features, axis=0)
    scaler = StandardScaler().fit(all_train_raw)

    # Step 2: 按股票构建完整序列后按索引切
    X_train_list, y_train_list = [], []
    X_val_list, y_val_list = [], []
    X_test_list, y_test_list = [], []
    test_ret_list = []

    for sym in SYMBOLS:
        info = per_stock_splits[sym]
        df = info["df"]
        n = info["n"]
        n_train = info["n_train"]
        n_val = info["n_val"]

        X_all_raw = df[FEATURE_COLS_V2].values.astype(np.float32)
        X_all = scaler.transform(X_all_raw).astype(np.float32)
        returns_all = df["returns"].values.astype(np.float32)

        # 序列索引 i: 使用 X_all[i-SEQ_LEN:i] 预测 returns_all[i]
        # 训练集: i ∈ [SEQ_LEN, n_train)
        # 验证集: i ∈ [n_train, n_train+n_val)
        # 测试集: i ∈ [n_train+n_val, n)
        def _build(indices):
            X = np.stack([X_all[i - SEQ_LEN : i] for i in indices])
            r = returns_all[indices]
            y = (r > 0).astype(np.int64)
            return X, y, r

        tr_idx = list(range(SEQ_LEN, n_train))
        va_idx = list(range(n_train, n_train + n_val))
        te_idx = list(range(n_train + n_val, n))

        if tr_idx:
            Xt, yt, _ = _build(tr_idx)
            X_train_list.append(Xt)
            y_train_list.append(yt)
        if va_idx:
            Xv, yv, _ = _build(va_idx)
            X_val_list.append(Xv)
            y_val_list.append(yv)
        if te_idx:
            Xe, ye, re = _build(te_idx)
            X_test_list.append(Xe)
            y_test_list.append(ye)
            test_ret_list.append(re)

        meta["per_stock_counts"][sym] = {
            "total_rows": n,
            "train_seqs": len(tr_idx),
            "val_seqs": len(va_idx),
            "test_seqs": len(te_idx),
        }

    X_train = np.concatenate(X_train_list, axis=0)
    y_train = np.concatenate(y_train_list, axis=0)
    X_val = np.concatenate(X_val_list, axis=0)
    y_val = np.concatenate(y_val_list, axis=0)
    X_test = np.concatenate(X_test_list, axis=0)
    y_test = np.concatenate(y_test_list, axis=0)
    test_ret = np.concatenate(test_ret_list, axis=0)

    # 训练集内跨股 shuffle（按 seed，保证复现）
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(len(X_train))
    X_train = X_train[perm]
    y_train = y_train[perm]

    return SplitArrays(X_train, y_train, X_val, y_val, X_test, y_test, test_ret), scaler, meta


# =========================================================
# 训练
# =========================================================

def get_lr_schedule(optimizer, warmup_epochs: int, total_epochs: int):
    """Linear warmup + cosine decay 复合调度器。"""
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return (epoch + 1) / warmup_epochs
        progress = (epoch - warmup_epochs) / max(1, total_epochs - warmup_epochs)
        return 0.5 * (1.0 + math.cos(math.pi * progress))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)


def train_one_config(
    data: SplitArrays,
    *,
    lr: float,
    dropout: float,
    d_model: int = 128,
    nhead: int = 8,
    num_layers: int = 3,
    epochs: int = 40,
    patience: int = 8,
    warmup: int = 3,
) -> dict:
    input_size = data.X_train.shape[2]
    model = TransformerModel(
        input_size=input_size,
        d_model=d_model,
        nhead=nhead,
        num_layers=num_layers,
        dropout=dropout,
    ).to(DEVICE)

    # 类别平衡 + 代价敏感（借鉴聚宽社区17113海龟体系：亏损样本权重2x）
    n_pos = int((data.y_train == 1).sum())
    n_neg = int((data.y_train == 0).sum())
    pos_weight = torch.tensor([n_neg / max(n_pos, 1), n_pos / max(n_neg, 1)], dtype=torch.float32, device=DEVICE)
    # 类别 0（下跌/亏损样本）权重 = 类别平衡基础 × 2.0 倍代价系数
    # 让模型学到"宁可错过上涨，不可踏入下跌"的代价敏感偏好
    COST_RATIO = 2.0
    class_weight = torch.tensor(
        [COST_RATIO, n_pos / max(n_neg, 1)],
        dtype=torch.float32,
        device=DEVICE,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weight)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = get_lr_schedule(optimizer, warmup_epochs=warmup, total_epochs=epochs)

    X_tr_t = torch.from_numpy(data.X_train).to(DEVICE)
    y_tr_t = torch.from_numpy(data.y_train).to(DEVICE)
    X_va_t = torch.from_numpy(data.X_val).to(DEVICE)
    y_va_t = torch.from_numpy(data.y_val).to(DEVICE)

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0
    history = []

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(X_tr_t))
        total_loss = 0.0
        n_batches = 0
        for start in range(0, len(X_tr_t), BATCH_SIZE):
            idx = perm[start : start + BATCH_SIZE]
            optimizer.zero_grad()
            logits = model(X_tr_t[idx])
            loss = criterion(logits, y_tr_t[idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        scheduler.step()
        avg_train_loss = total_loss / max(n_batches, 1)

        model.eval()
        with torch.no_grad():
            val_logits = model(X_va_t)
            val_loss = criterion(val_logits, y_va_t).item()
            val_probs_up = F.softmax(val_logits, dim=1)[:, 1].cpu().numpy()

        val_pred = (val_probs_up > 0.5).astype(np.int64)
        val_acc = float((val_pred == data.y_val).mean())

        history.append({
            "epoch": epoch + 1,
            "train_loss": round(avg_train_loss, 5),
            "val_loss": round(val_loss, 5),
            "val_acc": round(val_acc, 4),
            "lr": round(optimizer.param_groups[0]["lr"], 7),
        })

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                break

    # 恢复最佳
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_logits = model(X_va_t)
        val_probs_up = F.softmax(val_logits, dim=1)[:, 1].cpu().numpy()
    thresh, f1 = learn_threshold(val_probs_up, data.y_val)

    return {
        "model": model,
        "best_state": best_state,
        "best_val_loss": best_val_loss,
        "threshold": thresh,
        "val_f1": f1,
        "val_acc": float(((val_probs_up > thresh).astype(np.int64) == data.y_val).mean()),
        "n_epochs": epoch + 1,
        "history": history,
        "config": {
            "lr": lr,
            "dropout": dropout,
            "d_model": d_model,
            "nhead": nhead,
            "num_layers": num_layers,
        },
    }


def learn_threshold(probs_up: np.ndarray, y_true: np.ndarray) -> tuple[float, float]:
    """在验证集上扫阈值，选 F1 最大的一个。返回 (threshold, f1)."""
    best_t, best_f1 = 0.5, 0.0
    for t in np.linspace(0.35, 0.65, 31):
        pred = (probs_up > t).astype(np.int64)
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-10)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t, float(best_f1)


# =========================================================
# 主流程
# =========================================================

def main():
    print("=" * 70)
    print("DLQI: Transformer 多股联合训练（多股联合 · 24 特征 · 阈值学习）")
    print(f"设备: {DEVICE} | 股票池: {SYMBOLS}")
    print("=" * 70)

    print("\n[1/3] 准备数据集...")
    data, scaler, data_meta = prepare_dataset()
    print(f"  train seqs: {len(data.X_train)}")
    print(f"  val   seqs: {len(data.X_val)}")
    print(f"  test  seqs: {len(data.X_test)}")
    print(f"  feature dim: {data.X_train.shape[2]} (expected 24)")
    print(f"  train class balance: up={int((data.y_train==1).sum())} / down={int((data.y_train==0).sum())}")

    print("\n[2/3] 超参搜索（CPU 快速版：2 组配置，每组最多 15 epochs + 早停）")
    search_configs = [
        {"lr": 3e-4, "dropout": 0.2, "d_model": 64, "nhead": 4, "num_layers": 2},
        {"lr": 5e-4, "dropout": 0.3, "d_model": 64, "nhead": 4, "num_layers": 2},
    ]

    best = None
    search_log = []
    for i, cfg in enumerate(search_configs, 1):
        print(f"\n  [{i}/{len(search_configs)}] lr={cfg['lr']} dropout={cfg['dropout']} ... ", end="", flush=True)
        t0 = datetime.now()
        result = train_one_config(data, **cfg, epochs=15, patience=5)
        elapsed = (datetime.now() - t0).total_seconds()
        print(
            f"done | epochs={result['n_epochs']} "
            f"val_loss={result['best_val_loss']:.4f} "
            f"τ*={result['threshold']:.3f} F1={result['val_f1']:.4f} "
            f"acc={result['val_acc']:.3f} | {elapsed:.0f}s"
        )
        search_log.append({
            "config": result["config"],
            "n_epochs": result["n_epochs"],
            "best_val_loss": round(result["best_val_loss"], 5),
            "threshold": result["threshold"],
            "val_f1": round(result["val_f1"], 4),
            "val_acc": round(result["val_acc"], 4),
            "elapsed_sec": round(elapsed, 1),
        })
        if best is None or result["val_f1"] > best["val_f1"]:
            best = result

    print("\n[3/3] 保存主模型")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"transformer_{ts}"
    out_dir = MODELS_DIR / model_id
    out_dir.mkdir(parents=True, exist_ok=True)

    torch.save(best["best_state"], out_dir / "model.pt")
    joblib.dump(scaler, out_dir / "scaler.pkl")

    # 测试集 zero-shot 评估（使用学到的阈值）
    model = best["model"]
    model.eval()
    X_te_t = torch.from_numpy(data.X_test).to(DEVICE)
    with torch.no_grad():
        te_logits = model(X_te_t)
        te_probs = F.softmax(te_logits, dim=1)[:, 1].cpu().numpy()
    te_pred = (te_probs > best["threshold"]).astype(np.int64)
    te_acc = float((te_pred == data.y_test).mean())

    metadata = {
        "model_id": model_id,
        "model_type": "transformer",
        "symbol": "MULTI",
        "task_type": "classification",
        "is_primary": True,
        "features": FEATURE_COLS_V2,
        "seq_len": SEQ_LEN,
        "threshold": best["threshold"],  # 回测/推理使用的决策阈值
        "best_config": best["config"],
        "metrics": {
            "val_loss": round(best["best_val_loss"], 5),
            "val_f1": round(best["val_f1"], 4),
            "val_acc": round(best["val_acc"], 4),
            "test_acc": round(te_acc, 4),
            "direction_accuracy": round(te_acc, 4),  # 兼容 run_pipeline 分析
        },
        "data": {
            "train_seqs": len(data.X_train),
            "val_seqs": len(data.X_val),
            "test_seqs": len(data.X_test),
            "per_stock": data_meta["per_stock_counts"],
        },
        "search_log": search_log,
        "training": {
            "batch_size": BATCH_SIZE,
            "optimizer": "AdamW",
            "weight_decay": 1e-4,
            "scheduler": "linear_warmup_3 + cosine_decay",
            "seed": SEED,
            "n_epochs": best["n_epochs"],
            "history_tail": best["history"][-5:],
        },
        "created_at": datetime.now().isoformat(),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

    print(f"\n主模型已保存: {out_dir}")
    print(f"  d_model={best['config']['d_model']} heads={best['config']['nhead']} layers={best['config']['num_layers']}")
    print(f"  dropout={best['config']['dropout']} lr={best['config']['lr']}")
    print(f"  训练 epochs: {best['n_epochs']}")
    print(f"  验证 F1:    {best['val_f1']:.4f}")
    print(f"  验证 accuracy: {best['val_acc']:.4f}")
    print(f"  测试 accuracy: {te_acc:.4f}")
    print(f"  决策阈值 τ*:   {best['threshold']:.4f}")


if __name__ == "__main__":
    main()
