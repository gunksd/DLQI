"""
模型加载与推理服务
从 data/models/ 扫描已训练模型，按需加载并生成预测
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None
    nn = None

from app.core.config import settings


# ==================== 模型架构定义 ====================
# 与 Colab 训练时完全一致的网络结构
# 仅在 PyTorch 可用时定义

if HAS_TORCH:
    class LSTMModel(nn.Module):
        def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.2):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=input_size, hidden_size=hidden_size,
                num_layers=num_layers, dropout=dropout if num_layers > 1 else 0,
                batch_first=True, bidirectional=True
            )
            self.attention = nn.MultiheadAttention(
                embed_dim=hidden_size * 2, num_heads=4, dropout=dropout, batch_first=True
            )
            self.fc = nn.Sequential(
                nn.Linear(hidden_size * 2, hidden_size),
                nn.ReLU(), nn.Dropout(dropout),
                nn.Linear(hidden_size, 1)
            )

        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
            return self.fc(attn_out[:, -1, :])

    class TransformerModel(nn.Module):
        def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, dropout=0.2):
            super().__init__()
            self.d_model = d_model
            self.input_proj = nn.Linear(input_size, d_model)
            # 正弦位置编码（不需要学习，小数据更稳定）
            pe = torch.zeros(500, d_model)
            position = torch.arange(0, 500, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term)
            self.register_buffer('pe', pe.unsqueeze(0))  # (1, 500, d_model)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
                dropout=dropout, batch_first=True
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
            self.fc = nn.Sequential(
                nn.Linear(d_model, d_model // 2),
                nn.ReLU(), nn.Dropout(dropout),
                nn.Linear(d_model // 2, 1)
            )

        def forward(self, x):
            seq_len = x.size(1)
            x = self.input_proj(x)
            x = x + self.pe[:, :seq_len, :]
            # 因果掩码：防止未来信息泄露
            mask = nn.Transformer.generate_square_subsequent_mask(seq_len, device=x.device)
            x = self.transformer(x, mask=mask)
            return self.fc(x[:, -1, :])


# ==================== 模型服务 ====================

class ModelManager:
    """管理所有已训练模型的加载、缓存和推理"""

    def __init__(self):
        self._models_dir = settings.MODEL_DIR
        self._metadata_cache: Dict[str, dict] = {}
        self._loaded_models: Dict[str, Any] = {}
        self._loaded_scalers: Dict[str, Any] = {}
        self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if HAS_TORCH else None
        self._scan_models()

    def _scan_models(self):
        """扫描磁盘上的所有模型"""
        self._metadata_cache.clear()
        if not os.path.isdir(self._models_dir):
            return
        for name in os.listdir(self._models_dir):
            meta_path = os.path.join(self._models_dir, name, 'metadata.json')
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    self._metadata_cache[name] = json.load(f)

    def refresh(self):
        """重新扫描模型目录"""
        self._scan_models()

    # ---------- 查询接口 ----------

    def list_models(self) -> List[dict]:
        """列出所有模型及其元数据"""
        results = []
        for model_id, meta in self._metadata_cache.items():
            results.append(self._format_model_info(model_id, meta))
        results.sort(key=lambda x: x['created_at'], reverse=True)
        return results

    def get_model_info(self, model_id: str) -> Optional[dict]:
        """获取单个模型详情"""
        meta = self._metadata_cache.get(model_id)
        if not meta:
            return None
        return self._format_model_info(model_id, meta)

    def list_by_symbol(self, symbol: str) -> List[dict]:
        """按股票代码筛选模型"""
        return [
            self._format_model_info(mid, meta)
            for mid, meta in self._metadata_cache.items()
            if meta.get('symbol') == symbol
        ]

    def list_by_type(self, model_type: str) -> List[dict]:
        """按模型类型筛选"""
        return [
            self._format_model_info(mid, meta)
            for mid, meta in self._metadata_cache.items()
            if meta.get('model_type') == model_type
        ]

    def get_symbols(self) -> List[str]:
        """获取所有有模型的股票代码"""
        symbols = set()
        for meta in self._metadata_cache.values():
            if 'symbol' in meta:
                symbols.add(meta['symbol'])
        return sorted(symbols)

    def get_model_types(self) -> List[str]:
        """获取所有模型类型"""
        types = set()
        for meta in self._metadata_cache.values():
            if 'model_type' in meta:
                types.add(meta['model_type'])
        return sorted(types)

    # ---------- 模型加载 ----------

    def _load_model(self, model_id: str):
        """按需加载模型到内存"""
        if model_id in self._loaded_models:
            return self._loaded_models[model_id]

        meta = self._metadata_cache.get(model_id)
        if not meta:
            raise ValueError(f"模型 {model_id} 不存在")

        model_dir = os.path.join(self._models_dir, model_id)
        model_type = meta['model_type']
        features = meta.get('features', [])
        input_size = len(features)

        if model_type == 'lstm':
            model = LSTMModel(input_size=input_size)
            state = torch.load(
                os.path.join(model_dir, 'model.pt'),
                map_location=self._device,
                weights_only=True
            )
            model.load_state_dict(state)
            model.to(self._device)
            model.eval()

        elif model_type == 'transformer':
            model = TransformerModel(input_size=input_size)
            state = torch.load(
                os.path.join(model_dir, 'model.pt'),
                map_location=self._device,
                weights_only=True
            )
            model.load_state_dict(state)
            model.to(self._device)
            model.eval()

        elif model_type == 'lightgbm':
            import lightgbm as lgb
            model = lgb.Booster(model_file=os.path.join(model_dir, 'model.txt'))

        elif model_type == 'xgboost':
            import xgboost as xgb
            model = xgb.Booster()
            model.load_model(os.path.join(model_dir, 'model.json'))

        else:
            raise ValueError(f"未知模型类型: {model_type}")

        scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
        self._loaded_models[model_id] = model
        self._loaded_scalers[model_id] = scaler
        return model

    # ---------- 预测接口 ----------

    def predict(self, model_id: str, df: pd.DataFrame, sequence_length: int = 60) -> dict:
        """
        用指定模型对数据做预测
        df: 原始OHLCV数据 (columns: open, high, low, close, volume)
        返回: {predictions: [...], dates: [...], directions: [...]}
        """
        meta = self._metadata_cache.get(model_id)
        if not meta:
            raise ValueError(f"模型 {model_id} 不存在")

        model = self._load_model(model_id)
        scaler = self._loaded_scalers[model_id]
        model_type = meta['model_type']

        # 特征工程 — 与训练时完全一致
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
        df = df.dropna()

        feature_cols = ['open', 'high', 'low', 'close', 'volume',
                        'returns', 'ma_5', 'ma_20', 'volatility', 'rsi', 'macd', 'macd_signal']
        X_raw = df[feature_cols].values
        X_scaled = scaler.transform(X_raw)

        # 构建序列
        X_seq = []
        for i in range(sequence_length, len(X_scaled)):
            X_seq.append(X_scaled[i - sequence_length:i])
        X_seq = np.array(X_seq)

        dates = df.index[sequence_length:] if isinstance(df.index, pd.DatetimeIndex) else list(range(len(X_seq)))
        if 'date' in df.columns:
            dates = df['date'].iloc[sequence_length:].tolist()

        # 推理
        if model_type in ('lstm', 'transformer'):
            with torch.no_grad():
                tensor = torch.FloatTensor(X_seq).to(self._device)
                preds = model(tensor).squeeze().cpu().numpy()
        elif model_type == 'lightgbm':
            X_flat = X_seq.reshape(X_seq.shape[0], -1)
            preds = model.predict(X_flat)
        elif model_type == 'xgboost':
            import xgboost as xgb
            X_flat = X_seq.reshape(X_seq.shape[0], -1)
            preds = model.predict(xgb.DMatrix(X_flat))
        else:
            preds = np.zeros(len(X_seq))

        # 方向: 正=涨, 负=跌
        directions = ['up' if p > 0 else 'down' for p in preds]
        close_prices = df['close'].iloc[sequence_length:].tolist()

        return {
            'predictions': preds.tolist(),
            'dates': [str(d) for d in dates],
            'directions': directions,
            'close_prices': close_prices,
        }

    # ---------- 特征重要性 ----------

    def get_feature_importance(self, model_id: str) -> Optional[List[dict]]:
        """获取模型特征重要性 (仅树模型支持)"""
        meta = self._metadata_cache.get(model_id)
        if not meta:
            return None

        model_type = meta['model_type']
        features = meta.get('features', [])
        sequence_length = 60

        if model_type == 'lightgbm':
            model = self._load_model(model_id)
            raw_imp = model.feature_importance(importance_type='gain')
            # 特征名是 feat_0 .. feat_(seq*n_features-1)
            # 按原始特征聚合
            n_features = len(features)
            agg = np.zeros(n_features)
            for i, v in enumerate(raw_imp):
                agg[i % n_features] += v
            total = agg.sum()
            if total > 0:
                agg = agg / total
            result = []
            for i, name in enumerate(features):
                result.append({'name': name, 'importance': round(float(agg[i]), 4), 'rank': 0})
            result.sort(key=lambda x: x['importance'], reverse=True)
            for rank, item in enumerate(result, 1):
                item['rank'] = rank
            return result

        elif model_type == 'xgboost':
            model = self._load_model(model_id)
            raw_imp = model.get_score(importance_type='gain')
            n_features = len(features)
            agg = np.zeros(n_features)
            for key, val in raw_imp.items():
                idx = int(key.replace('f', ''))
                agg[idx % n_features] += val
            total = agg.sum()
            if total > 0:
                agg = agg / total
            result = []
            for i, name in enumerate(features):
                result.append({'name': name, 'importance': round(float(agg[i]), 4), 'rank': 0})
            result.sort(key=lambda x: x['importance'], reverse=True)
            for rank, item in enumerate(result, 1):
                item['rank'] = rank
            return result

        else:
            # 深度学习模型：用置换重要性法（Permutation Importance）
            # 需要用真实数据，随机数据会导致模型输出坍缩
            if not HAS_TORCH:
                n = len(features)
                return [{'name': name, 'importance': round(1.0 / n, 4), 'rank': i + 1}
                        for i, name in enumerate(features)]

            model = self._load_model(model_id)
            scaler = self._loaded_scalers[model_id]
            n_features = len(features)

            # 加载真实数据
            import glob as glob_mod
            raw_dir = os.path.join(os.path.dirname(self._models_dir), 'raw')
            csv_files = sorted(glob_mod.glob(os.path.join(raw_dir, 'us_*.csv')))
            csv_files = [f for f in csv_files if 'idx_' not in os.path.basename(f)][:5]

            all_seqs = []
            for csv_path in csv_files:
                try:
                    df = pd.read_csv(csv_path)
                    col_map = {'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
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
                    df = df.dropna()
                    X = scaler.transform(df[features].values)
                    for i in range(60, min(len(X), 120)):
                        all_seqs.append(X[i-60:i])
                except Exception:
                    continue

            if not all_seqs:
                n = len(features)
                return [{'name': name, 'importance': round(1.0 / n, 4), 'rank': i + 1}
                        for i, name in enumerate(features)]

            base_input = torch.FloatTensor(np.array(all_seqs)).to(self._device)

            model.eval()
            with torch.no_grad():
                base_output = model(base_input).squeeze()
                importances = np.zeros(n_features)
                for feat_idx in range(n_features):
                    permuted = base_input.clone()
                    perm_idx = torch.randperm(len(base_input))
                    permuted[:, :, feat_idx] = permuted[perm_idx, :, feat_idx]
                    perm_output = model(permuted).squeeze()
                    importances[feat_idx] = (base_output - perm_output).abs().mean().item()

            total = importances.sum()
            if total > 0:
                importances = importances / total

            result = []
            for i, name in enumerate(features):
                result.append({'name': name, 'importance': round(float(importances[i]), 4), 'rank': 0})
            result.sort(key=lambda x: x['importance'], reverse=True)
            for rank, item in enumerate(result, 1):
                item['rank'] = rank
            return result

    # ---------- 内部格式化 ----------

    def _format_model_info(self, model_id: str, meta: dict) -> dict:
        """将 metadata.json 转换为 API 响应格式"""
        model_type = meta.get('model_type', 'unknown')
        type_names = {
            'lstm': 'BiLSTM + Attention',
            'transformer': 'Transformer Encoder',
            'lightgbm': 'LightGBM',
            'xgboost': 'XGBoost',
        }
        return {
            'model_id': model_id,
            'name': f"{model_type.upper()} - {meta.get('symbol', '?')}",
            'model_type': model_type,
            'model_type_display': type_names.get(model_type, model_type),
            'symbol': meta.get('symbol', ''),
            'status': 'trained',
            'val_loss': meta.get('val_loss'),
            'epochs': meta.get('epochs'),
            'features': meta.get('features', []),
            'data_points': meta.get('data_points'),
            'created_at': meta.get('created_at', ''),
            'task_id': meta.get('task_id', ''),
        }


# 全局单例
model_manager = ModelManager()
