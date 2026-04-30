#!/usr/bin/env python3
"""
DLQI: A 股模型训练脚本
训练 LightGBM / XGBoost / LSTM / Transformer 四种模型
用法: cd /home/awan/DLQI && backend/venv/bin/python scripts/train_cn_models.py
"""

import os, sys, json, warnings, joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MODELS_DIR = DATA_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

import torch
import torch.nn as nn

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SYMBOLS = ["600519", "601318", "600036", "300750", "002594"]
FEATURE_COLS = ['open','high','low','close','volume','returns','ma_5','ma_20',
                'volatility','rsi','macd','macd_signal']
SEQ_LENGTH = 60


# ── 模型架构 ──

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


class TransformerClassifier(nn.Module):
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


# ── 特征工程 ──

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['ma_5'] = df['close'].rolling(5).mean()
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


# ── 数据准备 ──

def prepare_data(symbol: str):
    csv_path = RAW_DIR / f"cn_{symbol}.csv"
    df = pd.read_csv(csv_path)
    df = engineer_features(df)
    X_raw = df[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    X_seq, y_seq = [], []
    for i in range(SEQ_LENGTH, len(X_scaled)):
        X_seq.append(X_scaled[i - SEQ_LENGTH:i])
        y_seq.append(df['returns'].iloc[i])
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)

    n = len(X_seq)
    n_train = int(n * 0.7)
    n_val = int(n * 0.15)
    X_train, y_train = X_seq[:n_train], y_seq[:n_train]
    X_val, y_val = X_seq[n_train:n_train+n_val], y_seq[n_train:n_train+n_val]
    X_test, y_test = X_seq[n_train+n_val:], y_seq[n_train+n_val:]
    return X_train, y_train, X_val, y_val, X_test, y_test, scaler, len(df)


def save_model(model_dir: Path, model, scaler, meta):
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, model_dir / "scaler.pkl")
    (model_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))


# ── LightGBM 训练 ──

def train_lightgbm(symbol: str):
    X_train, y_train, X_val, y_val, X_test, y_test, scaler, n_data = prepare_data(symbol)
    import lightgbm as lgb

    X_tr_flat = X_train.reshape(len(X_train), -1)
    X_va_flat = X_val.reshape(len(X_val), -1)

    ds_train = lgb.Dataset(X_tr_flat, label=y_train)
    ds_val = lgb.Dataset(X_va_flat, label=y_val, reference=ds_train)

    params = {
        "objective": "regression", "metric": "rmse", "boosting_type": "gbdt",
        "num_leaves": 31, "learning_rate": 0.05, "feature_fraction": 0.8,
        "bagging_fraction": 0.8, "bagging_freq": 5, "verbose": -1,
    }
    model = lgb.train(params, ds_train, num_boost_round=500,
                      valid_sets=[ds_val], callbacks=[lgb.early_stopping(50, verbose=False)])

    val_pred = model.predict(X_va_flat)
    val_rmse = float(np.sqrt(np.mean((val_pred - y_val) ** 2)))
    val_dir_acc = float(np.mean((val_pred > 0) == (y_val > 0)))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"lightgbm_{symbol}_{ts}"
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_dir / "model.txt"), num_iteration=model.best_iteration)
    save_model(model_dir, model, scaler, {
        "model_id": model_id, "model_type": "lightgbm", "symbol": symbol,
        "features": FEATURE_COLS, "data_points": n_data,
        "metrics": {"val_rmse": round(val_rmse, 6), "direction_accuracy": round(val_dir_acc, 4)},
        "created_at": datetime.now().isoformat(),
    })
    return model_id, val_rmse, val_dir_acc


# ── XGBoost 训练 ──

def train_xgboost(symbol: str):
    X_train, y_train, X_val, y_val, X_test, y_test, scaler, n_data = prepare_data(symbol)
    import xgboost as xgb

    X_tr_flat = X_train.reshape(len(X_train), -1)
    X_va_flat = X_val.reshape(len(X_val), -1)

    dtrain = xgb.DMatrix(X_tr_flat, label=y_train)
    dval = xgb.DMatrix(X_va_flat, label=y_val)

    params = {
        "objective": "reg:squarederror", "eval_metric": "rmse",
        "max_depth": 6, "learning_rate": 0.05, "subsample": 0.8,
        "colsample_bytree": 0.8, "verbosity": 0,
    }
    model = xgb.train(params, dtrain, num_boost_round=500,
                      evals=[(dval, "val")], early_stopping_rounds=50, verbose_eval=False)

    val_pred = model.predict(dval)
    val_rmse = float(np.sqrt(np.mean((val_pred - y_val) ** 2)))
    val_dir_acc = float(np.mean((val_pred > 0) == (y_val > 0)))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"xgboost_{symbol}_{ts}"
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_dir / "model.json"))
    save_model(model_dir, model, scaler, {
        "model_id": model_id, "model_type": "xgboost", "symbol": symbol,
        "features": FEATURE_COLS, "data_points": n_data,
        "metrics": {"val_rmse": round(val_rmse, 6), "direction_accuracy": round(val_dir_acc, 4)},
        "created_at": datetime.now().isoformat(),
    })
    return model_id, val_rmse, val_dir_acc


# ── LSTM 训练 ──

def train_lstm(symbol: str, epochs=50):
    X_train, y_train, X_val, y_val, X_test, y_test, scaler, n_data = prepare_data(symbol)
    input_size = X_train.shape[2]
    model = LSTMModel(input_size=input_size).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.MSELoss()

    X_tr_t = torch.FloatTensor(X_train).to(DEVICE)
    y_tr_t = torch.FloatTensor(y_train).to(DEVICE)
    X_va_t = torch.FloatTensor(X_val).to(DEVICE)
    y_va_t = torch.FloatTensor(y_val).to(DEVICE)

    best_val_loss = float('inf')
    best_state = None
    patience_counter = 0

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        pred = model(X_tr_t).squeeze()
        loss = criterion(pred, y_tr_t)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_pred = model(X_va_t).squeeze()
            val_loss = criterion(val_pred, y_va_t).item()
        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= 15:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_pred_np = model(X_va_t).squeeze().cpu().numpy()
    val_rmse = float(np.sqrt(np.mean((val_pred_np - y_val) ** 2)))
    val_dir_acc = float(np.mean((val_pred_np > 0) == (y_val > 0)))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"lstm_{symbol}_{ts}"
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, model_dir / "model.pt")
    save_model(model_dir, model, scaler, {
        "model_id": model_id, "model_type": "lstm", "symbol": symbol,
        "features": FEATURE_COLS, "data_points": n_data,
        "metrics": {"val_rmse": round(val_rmse, 6), "direction_accuracy": round(val_dir_acc, 4)},
        "val_loss": round(best_val_loss, 6), "epochs": epoch + 1,
        "created_at": datetime.now().isoformat(),
    })
    return model_id, val_rmse, val_dir_acc


# ── Transformer (MULTI) 训练 ──

def train_transformer_multi(epochs=60):
    """联合训练：所有股票数据合并训练一个 Transformer 分类模型"""
    all_X, all_y = [], []
    total_data = 0
    for symbol in SYMBOLS:
        X_train, y_train, _, _, _, _, scaler_tmp, n_data = prepare_data(symbol)
        all_X.append(X_train)
        all_y.append(y_train)
        total_data += n_data

    X_all = np.concatenate(all_X)
    y_all = np.concatenate(all_y)

    # 重新 fit scaler on all data
    all_raw = []
    for symbol in SYMBOLS:
        df = pd.read_csv(RAW_DIR / f"cn_{symbol}.csv")
        df = engineer_features(df)
        all_raw.append(df[FEATURE_COLS].values)
    scaler = StandardScaler()
    scaler.fit(np.concatenate(all_raw))

    # Re-scale
    n = len(X_all)
    perm = np.random.permutation(n)
    X_all = X_all[perm]
    y_all = y_all[perm]

    n_train = int(n * 0.85)
    X_train, y_train = X_all[:n_train], y_all[:n_train]
    X_val, y_val = X_all[n_train:], y_all[n_train:]

    # 分类标签
    y_train_cls = (y_train > 0).astype(np.int64)
    y_val_cls = (y_val > 0).astype(np.int64)

    input_size = X_train.shape[2]
    model = TransformerClassifier(input_size=input_size).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    X_tr_t = torch.FloatTensor(X_train).to(DEVICE)
    y_tr_t = torch.LongTensor(y_train_cls).to(DEVICE)
    X_va_t = torch.FloatTensor(X_val).to(DEVICE)
    y_va_t = torch.LongTensor(y_val_cls).to(DEVICE)

    best_val_loss = float('inf')
    best_state = None
    batch_size = 256

    for epoch in range(epochs):
        model.train()
        indices = torch.randperm(len(X_tr_t))
        total_loss = 0
        for start in range(0, len(X_tr_t), batch_size):
            idx = indices[start:start+batch_size]
            optimizer.zero_grad()
            out = model(X_tr_t[idx])
            loss = criterion(out, y_tr_t[idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_out = model(X_va_t)
            val_loss = criterion(val_out, y_va_t).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_out = model(X_va_t)
        val_pred_cls = val_out.argmax(dim=1).cpu().numpy()
    val_dir_acc = float(np.mean(val_pred_cls == y_val_cls))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = f"transformer_MULTI_{ts}"
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, model_dir / "model.pt")
    save_model(model_dir, model, scaler, {
        "model_id": model_id, "model_type": "transformer", "symbol": "MULTI",
        "task_type": "classification",
        "features": FEATURE_COLS, "data_points": total_data,
        "metrics": {"val_loss": round(best_val_loss, 6), "direction_accuracy": round(val_dir_acc, 4)},
        "val_loss": round(best_val_loss, 6), "epochs": epochs,
        "created_at": datetime.now().isoformat(),
    })
    return model_id, best_val_loss, val_dir_acc


# ── 主流程 ──

def main():
    print("=" * 60)
    print("DLQI: A 股模型训练")
    print(f"股票池: {SYMBOLS}")
    print(f"设备: {DEVICE}")
    print("=" * 60)

    results = []

    # 1. 每只股票训练 LightGBM + XGBoost + LSTM
    for symbol in SYMBOLS:
        print(f"\n{'─' * 40}")
        print(f"股票: {symbol}")
        print(f"{'─' * 40}")

        for name, func in [("LightGBM", train_lightgbm), ("XGBoost", train_xgboost), ("LSTM", train_lstm)]:
            print(f"  训练 {name} ... ", end="", flush=True)
            try:
                mid, rmse, acc = func(symbol)
                print(f"RMSE={rmse:.6f}  DirAcc={acc:.1%}  → {mid}")
                results.append({"model_id": mid, "type": name, "symbol": symbol, "rmse": rmse, "dir_acc": acc})
            except Exception as e:
                print(f"失败: {e}")

    # 2. 联合训练 Transformer
    print(f"\n{'─' * 40}")
    print("联合训练 Transformer (MULTI)")
    print(f"{'─' * 40}")
    print("  训练中 ... ", end="", flush=True)
    try:
        mid, vloss, acc = train_transformer_multi()
        print(f"ValLoss={vloss:.6f}  DirAcc={acc:.1%}  → {mid}")
        results.append({"model_id": mid, "type": "Transformer", "symbol": "MULTI", "rmse": vloss, "dir_acc": acc})
    except Exception as e:
        print(f"失败: {e}")

    print(f"\n{'=' * 60}")
    print(f"训练完成! 共 {len(results)} 个模型")
    for r in results:
        print(f"  {r['type']:<12} {r['symbol']:<8} DirAcc={r['dir_acc']:.1%}  → {r['model_id']}")
    print(f"模型保存在: {MODELS_DIR}")


if __name__ == "__main__":
    main()
