"""
训练编排服务 — 从 UI 触发完整的训练流程
复用现有 ModelTrainer + model_service 架构
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from typing import Callable
from loguru import logger
from sklearn.preprocessing import StandardScaler

from app.core.config import settings


# 特征工程 — 与 model_service.py 中推理时一致
FEATURE_COLS = [
    "open", "high", "low", "close", "volume",
    "returns", "ma_5", "ma_20", "volatility", "rsi", "macd", "macd_signal",
]


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """与推理时完全一致的特征工程"""
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
    df = df.dropna()
    return df


def run_training(params: dict, progress_cb: Callable):
    """
    完整训练流程（在线程池中执行）
    params: {symbol, model_type, sequence_length?, epochs?}
    """
    symbol = params["symbol"]
    model_type = params["model_type"]
    seq_len = params.get("sequence_length", 60)
    epochs = params.get("epochs", 50)

    progress_cb(5, f"获取 {symbol} 数据")

    # 1. 获取数据
    df = _fetch_data(symbol)
    if df is None or len(df) < 200:
        raise ValueError(f"数据不足: {symbol} 只有 {len(df) if df is not None else 0} 条记录")

    progress_cb(15, "特征工程")

    # 2. 特征工程
    df = _engineer_features(df)
    logger.info(f"特征工程完成: {len(df)} 条数据, {len(FEATURE_COLS)} 个特征")

    # 3. 构建目标变量（下一日收益率）
    df["target"] = df["returns"].shift(-1)
    df = df.dropna()

    progress_cb(20, "数据分割与标准化")

    # 4. 分割
    X_raw = df[FEATURE_COLS].values
    y = df["target"].values

    train_end = int(len(X_raw) * 0.7)
    val_end = int(len(X_raw) * 0.85)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw[:train_end])
    X_val_scaled = scaler.transform(X_raw[train_end:val_end])
    X_test_scaled = scaler.transform(X_raw[val_end:])

    y_train = y[:train_end]
    y_val = y[train_end:val_end]
    y_test = y[val_end:]

    progress_cb(30, f"训练 {model_type} 模型")

    # 5. 训练
    if model_type == "lightgbm":
        model, metrics = _train_lightgbm(X_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test, seq_len, progress_cb)
    elif model_type == "xgboost":
        model, metrics = _train_xgboost(X_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test, seq_len, progress_cb)
    elif model_type == "lstm":
        model, metrics = _train_lstm(X_scaled, y_train, X_val_scaled, y_val, seq_len, epochs, progress_cb)
    elif model_type == "transformer":
        model, metrics = _train_transformer(X_scaled, y_train, X_val_scaled, y_val, seq_len, epochs, progress_cb)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

    progress_cb(85, "保存模型")

    # 6. 保存
    model_id = f"{model_type}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    model_dir = os.path.join(settings.MODEL_DIR, model_id)
    os.makedirs(model_dir, exist_ok=True)

    # 保存 scaler
    joblib.dump(scaler, os.path.join(model_dir, "scaler.pkl"))

    # 保存模型
    if model_type in ("lightgbm",):
        model.save_model(os.path.join(model_dir, "model.txt"))
    elif model_type == "xgboost":
        model.save_model(os.path.join(model_dir, "model.json"))
    elif model_type in ("lstm", "transformer"):
        import torch
        torch.save(model.state_dict(), os.path.join(model_dir, "model.pt"))

    # 保存 metadata
    metadata = {
        "model_type": model_type,
        "symbol": symbol,
        "features": FEATURE_COLS,
        "data_points": len(df),
        "epochs": epochs if model_type == "lstm" else None,
        "val_loss": metrics.get("val_rmse"),
        "metrics": metrics,
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(model_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    progress_cb(95, "刷新模型列表")

    # 7. 刷新 ModelManager 缓存
    from app.services.model_service import model_manager
    model_manager.refresh()

    progress_cb(100, "训练完成")

    return {
        "model_id": model_id,
        "metrics": metrics,
    }


def _fetch_data(symbol: str) -> pd.DataFrame:
    """获取股票数据：优先本地 CSV，回退 yfinance"""
    data_dir = settings.DATA_DIR
    for prefix in ["us_", ""]:
        csv_path = os.path.join(data_dir, "raw", f"{prefix}{symbol}.csv")
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
            col_map = {"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            logger.info(f"从本地 CSV 加载 {symbol}: {len(df)} 条")
            return df

    # 回退到 yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5y", auto_adjust=True).reset_index()
        df = df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df["date"] = df["date"].dt.tz_localize(None)
        logger.info(f"从 yfinance 获取 {symbol}: {len(df)} 条")
        return df
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {e}")
        return None


def _build_sequences(X: np.ndarray, y: np.ndarray, seq_len: int):
    """构建时序序列（用于树模型展平 & LSTM）"""
    X_seq, y_seq = [], []
    for i in range(seq_len, len(X)):
        X_seq.append(X[i - seq_len:i])
        y_seq.append(y[i])
    return np.array(X_seq), np.array(y_seq)


def _train_lightgbm(X_train, y_train, X_val, y_val, X_test, y_test, seq_len, progress_cb):
    import lightgbm as lgb

    X_train_seq, y_train_seq = _build_sequences(X_train, y_train, seq_len)
    X_val_seq, y_val_seq = _build_sequences(X_val, y_val, seq_len)
    X_test_seq, y_test_seq = _build_sequences(X_test, y_test, seq_len)

    X_train_flat = X_train_seq.reshape(len(X_train_seq), -1)
    X_val_flat = X_val_seq.reshape(len(X_val_seq), -1)
    X_test_flat = X_test_seq.reshape(len(X_test_seq), -1)

    progress_cb(40, "LightGBM 训练中...")

    train_ds = lgb.Dataset(X_train_flat, label=y_train_seq)
    val_ds = lgb.Dataset(X_val_flat, label=y_val_seq, reference=train_ds)

    params = {
        "objective": "regression",
        "metric": "rmse",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }

    model = lgb.train(
        params, train_ds, num_boost_round=500,
        valid_sets=[val_ds],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )

    progress_cb(70, "评估模型...")

    preds = model.predict(X_test_flat)
    rmse = float(np.sqrt(np.mean((preds - y_test_seq) ** 2)))
    dir_acc = float(np.mean(np.sign(preds) == np.sign(y_test_seq)))

    return model, {"val_rmse": rmse, "direction_accuracy": dir_acc, "n_estimators": model.num_trees()}


def _train_xgboost(X_train, y_train, X_val, y_val, X_test, y_test, seq_len, progress_cb):
    import xgboost as xgb

    X_train_seq, y_train_seq = _build_sequences(X_train, y_train, seq_len)
    X_val_seq, y_val_seq = _build_sequences(X_val, y_val, seq_len)
    X_test_seq, y_test_seq = _build_sequences(X_test, y_test, seq_len)

    X_train_flat = X_train_seq.reshape(len(X_train_seq), -1)
    X_val_flat = X_val_seq.reshape(len(X_val_seq), -1)
    X_test_flat = X_test_seq.reshape(len(X_test_seq), -1)

    progress_cb(40, "XGBoost 训练中...")

    dtrain = xgb.DMatrix(X_train_flat, label=y_train_seq)
    dval = xgb.DMatrix(X_val_flat, label=y_val_seq)

    params = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    }

    model = xgb.train(
        params, dtrain, num_boost_round=500,
        evals=[(dval, "val")],
        early_stopping_rounds=50, verbose_eval=False,
    )

    progress_cb(70, "评估模型...")

    dtest = xgb.DMatrix(X_test_flat)
    preds = model.predict(dtest)
    rmse = float(np.sqrt(np.mean((preds - y_test_seq) ** 2)))
    dir_acc = float(np.mean(np.sign(preds) == np.sign(y_test_seq)))

    return model, {"val_rmse": rmse, "direction_accuracy": dir_acc}


def _train_lstm(X_train, y_train, X_val, y_val, seq_len, epochs, progress_cb):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    # 复用 model_service 中的 LSTM 架构
    from app.services.model_service import LSTMModel

    X_train_seq, y_train_seq = _build_sequences(X_train, y_train, seq_len)
    X_val_seq, y_val_seq = _build_sequences(X_val, y_val, seq_len)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_size = X_train_seq.shape[2]

    model = LSTMModel(input_size=input_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    train_ds = TensorDataset(
        torch.FloatTensor(X_train_seq),
        torch.FloatTensor(y_train_seq),
    )
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=False)

    X_val_t = torch.FloatTensor(X_val_seq).to(device)
    y_val_t = torch.FloatTensor(y_val_seq).to(device)

    best_val_loss = float("inf")
    best_state = None

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb).squeeze(), yb)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_val_t).squeeze()
            val_loss = criterion(val_preds, y_val_t).item()
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % max(1, epochs // 10) == 0:
            pct = 30 + int(50 * epoch / epochs)
            progress_cb(pct, f"LSTM epoch {epoch+1}/{epochs}, val_loss={val_loss:.6f}")

    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        preds = model(X_val_t).squeeze().cpu().numpy()
    dir_acc = float(np.mean(np.sign(preds) == np.sign(y_val_seq)))

    return model, {"val_rmse": float(np.sqrt(best_val_loss)), "direction_accuracy": dir_acc, "epochs": epochs}


def _train_transformer(X_train, y_train, X_val, y_val, seq_len, epochs, progress_cb):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    from app.services.model_service import TransformerModel

    X_train_seq, y_train_seq = _build_sequences(X_train, y_train, seq_len)
    X_val_seq, y_val_seq = _build_sequences(X_val, y_val, seq_len)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_size = X_train_seq.shape[2]

    model = TransformerModel(input_size=input_size).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    train_ds = TensorDataset(
        torch.FloatTensor(X_train_seq),
        torch.FloatTensor(y_train_seq),
    )
    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True)

    X_val_t = torch.FloatTensor(X_val_seq).to(device)
    y_val_t = torch.FloatTensor(y_val_seq).to(device)

    best_val_loss = float("inf")
    best_state = None
    patience, patience_counter = 15, 0

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb).squeeze(), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_val_t).squeeze()
            val_loss = criterion(val_preds, y_val_t).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Transformer early stopping at epoch {epoch+1}")
                break

        if epoch % max(1, epochs // 10) == 0:
            pct = 30 + int(50 * epoch / epochs)
            progress_cb(pct, f"Transformer epoch {epoch+1}/{epochs}, val_loss={val_loss:.6f}")

    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        preds = model(X_val_t).squeeze().cpu().numpy()
    dir_acc = float(np.mean(np.sign(preds) == np.sign(y_val_seq)))

    return model, {"val_rmse": float(np.sqrt(best_val_loss)), "direction_accuracy": dir_acc, "epochs": epochs}


# ==================== 多股票联合训练 ====================

def run_multi_stock_training(params: dict, progress_cb: Callable):
    """
    多股票联合训练（主要用于 Transformer）
    params: {model_type, sequence_length?, epochs?, max_stocks?}
    """
    import glob as glob_mod

    model_type = params.get("model_type", "transformer")
    seq_len = params.get("sequence_length", 60)
    epochs = params.get("epochs", 30)
    max_stocks = params.get("max_stocks")

    progress_cb(2, "扫描可用股票数据...")

    # 1. 收集所有 us_*.csv
    raw_dir = os.path.join(settings.DATA_DIR, "raw")
    csv_files = sorted(glob_mod.glob(os.path.join(raw_dir, "us_*.csv")))
    # 排除指数文件
    csv_files = [f for f in csv_files if "idx_" not in os.path.basename(f)]

    if not csv_files:
        raise ValueError(f"未找到股票数据文件: {raw_dir}/us_*.csv")

    if max_stocks and len(csv_files) > max_stocks:
        csv_files = csv_files[:max_stocks]

    total_files = len(csv_files)
    logger.info(f"多股票训练: 找到 {total_files} 只股票")
    progress_cb(5, f"加载 {total_files} 只股票数据...")

    # 2. 逐股票加载 + 特征工程
    all_dfs = []
    for i, csv_path in enumerate(csv_files):
        try:
            df = pd.read_csv(csv_path)
            col_map = {"Date": "date", "Open": "open", "High": "high",
                       "Low": "low", "Close": "close", "Volume": "volume"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            df = _engineer_features(df)
            df["target"] = df["returns"].shift(-1)
            df = df.dropna()
            if len(df) >= seq_len + 50:
                sym = os.path.basename(csv_path).replace("us_", "").replace(".csv", "")
                df["_symbol"] = sym
                all_dfs.append(df)
        except Exception as e:
            logger.warning(f"跳过 {csv_path}: {e}")

        if i % 50 == 0:
            pct = 5 + int(20 * i / total_files)
            progress_cb(pct, f"加载数据 {i+1}/{total_files}...")

    if not all_dfs:
        raise ValueError("没有足够数据的股票")

    logger.info(f"有效股票: {len(all_dfs)}, 总数据量: {sum(len(d) for d in all_dfs)}")
    progress_cb(25, f"构建序列 ({len(all_dfs)} 只股票)...")

    # 3. 逐股票分割 + 标准化 + 构建序列（避免跨股票边界）
    all_X_train, all_y_train = [], []
    all_X_val, all_y_val = [], []

    # 先合并所有训练数据来 fit scaler
    train_chunks = []
    for df in all_dfs:
        train_end = int(len(df) * 0.7)
        train_chunks.append(df[FEATURE_COLS].values[:train_end])

    scaler = StandardScaler()
    scaler.fit(np.concatenate(train_chunks, axis=0))

    for idx, df in enumerate(all_dfs):
        X_raw = df[FEATURE_COLS].values
        y = df["target"].values

        train_end = int(len(X_raw) * 0.7)
        val_end = int(len(X_raw) * 0.85)

        X_train_s = scaler.transform(X_raw[:train_end])
        X_val_s = scaler.transform(X_raw[train_end:val_end])
        y_train_s = y[:train_end]
        y_val_s = y[train_end:val_end]

        # 逐股票构建序列
        if len(X_train_s) > seq_len:
            Xt, yt = _build_sequences(X_train_s, y_train_s, seq_len)
            all_X_train.append(Xt)
            all_y_train.append(yt)
        if len(X_val_s) > seq_len:
            Xv, yv = _build_sequences(X_val_s, y_val_s, seq_len)
            all_X_val.append(Xv)
            all_y_val.append(yv)

        if idx % 100 == 0:
            pct = 25 + int(15 * idx / len(all_dfs))
            progress_cb(pct, f"构建序列 {idx+1}/{len(all_dfs)}...")

    X_train_all = np.concatenate(all_X_train, axis=0)
    y_train_all = np.concatenate(all_y_train, axis=0)
    X_val_all = np.concatenate(all_X_val, axis=0)
    y_val_all = np.concatenate(all_y_val, axis=0)

    # shuffle 训练集
    perm = np.random.permutation(len(X_train_all))
    X_train_all = X_train_all[perm]
    y_train_all = y_train_all[perm]

    logger.info(f"训练集: {X_train_all.shape}, 验证集: {X_val_all.shape}")
    progress_cb(40, f"开始训练 (train={len(X_train_all)}, val={len(X_val_all)})...")

    # 4. 训练
    if model_type == "transformer":
        model, metrics = _train_transformer_direct(
            X_train_all, y_train_all, X_val_all, y_val_all,
            epochs=epochs, progress_cb=progress_cb,
        )
    else:
        raise ValueError(f"多股票训练暂只支持 transformer, 不支持 {model_type}")

    progress_cb(90, "保存模型...")

    # 5. 保存
    model_id = f"{model_type}_MULTI_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    model_dir = os.path.join(settings.MODEL_DIR, model_id)
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(scaler, os.path.join(model_dir, "scaler.pkl"))

    import torch
    torch.save(model.state_dict(), os.path.join(model_dir, "model.pt"))

    metadata = {
        "model_type": model_type,
        "symbol": "MULTI",
        "features": FEATURE_COLS,
        "data_points": len(X_train_all) + len(X_val_all),
        "n_stocks": len(all_dfs),
        "epochs": epochs,
        "val_loss": metrics.get("val_rmse"),
        "metrics": metrics,
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(model_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    progress_cb(95, "刷新模型列表...")
    from app.services.model_service import model_manager
    model_manager.refresh()

    progress_cb(100, "多股票训练完成")
    return {"model_id": model_id, "metrics": metrics, "n_stocks": len(all_dfs)}


def _train_transformer_direct(X_train_seq, y_train_seq, X_val_seq, y_val_seq,
                               epochs, progress_cb):
    """直接用已构建好的序列数据训练 Transformer（跳过 _build_sequences）"""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    from app.services.model_service import TransformerModel

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_size = X_train_seq.shape[2]

    model = TransformerModel(input_size=input_size).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    train_ds = TensorDataset(
        torch.FloatTensor(X_train_seq),
        torch.FloatTensor(y_train_seq),
    )
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True)

    X_val_t = torch.FloatTensor(X_val_seq).to(device)
    y_val_t = torch.FloatTensor(y_val_seq).to(device)

    best_val_loss = float("inf")
    best_state = None
    patience, patience_counter = 10, 0

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb).squeeze(), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_val_t).squeeze()
            val_loss = criterion(val_preds, y_val_t).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Multi-stock Transformer early stopping at epoch {epoch+1}")
                break

        if epoch % max(1, epochs // 10) == 0:
            pct = 40 + int(45 * epoch / epochs)
            progress_cb(pct, f"Multi Transformer epoch {epoch+1}/{epochs}, val_loss={val_loss:.6f}")

    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        preds = model(X_val_t).squeeze().cpu().numpy()
    dir_acc = float(np.mean(np.sign(preds) == np.sign(y_val_seq)))

    return model, {"val_rmse": float(np.sqrt(best_val_loss)), "direction_accuracy": dir_acc, "epochs": epochs}
