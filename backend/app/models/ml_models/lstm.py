"""
LSTM深度学习模型
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from .base import BaseModel, register_model


class LSTMNetwork(nn.Module):
    """LSTM神经网络架构"""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = False
    ):
        super().__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1

        # LSTM层
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        # 全连接层
        fc_input_size = hidden_size * self.num_directions
        self.fc = nn.Sequential(
            nn.Linear(fc_input_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # LSTM前向传播
        lstm_out, _ = self.lstm(x)

        # 取最后一个时间步的输出
        if self.bidirectional:
            # 双向LSTM: 取前向最后时刻和后向第一时刻
            out = torch.cat((lstm_out[:, -1, :self.hidden_size],
                           lstm_out[:, 0, self.hidden_size:]), dim=1)
        else:
            out = lstm_out[:, -1, :]

        # 全连接层
        out = self.fc(out)
        return out.squeeze(-1)


@register_model('lstm')
class LSTMModel(BaseModel):
    """LSTM预测模型"""

    def __init__(self, name: str = 'lstm', params: Optional[Dict] = None):
        default_params = {
            'seq_length': 60,          # 序列长度
            'hidden_size': 128,        # 隐藏层大小
            'num_layers': 2,           # LSTM层数
            'dropout': 0.2,            # Dropout比例
            'bidirectional': False,    # 是否双向
            'learning_rate': 0.001,    # 学习率
            'batch_size': 64,          # 批次大小
            'epochs': 100,             # 训练轮数
            'early_stopping': 10,      # 早停轮数
            'device': 'cuda' if torch.cuda.is_available() else 'cpu'
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)
        self.device = torch.device(self.params['device'])
        self.scaler = None

    def build(self, input_size: int):
        """构建模型"""
        self.model = LSTMNetwork(
            input_size=input_size,
            hidden_size=self.params['hidden_size'],
            num_layers=self.params['num_layers'],
            dropout=self.params['dropout'],
            bidirectional=self.params['bidirectional']
        ).to(self.device)

        logger.info(f"LSTM模型已构建: input_size={input_size}, device={self.device}")

    def prepare_sequences(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备序列数据

        Args:
            X: 特征数据 (n_samples, n_features)
            y: 目标数据 (n_samples,)

        Returns:
            序列特征和目标 (n_sequences, seq_length, n_features), (n_sequences,)
        """
        seq_length = self.params['seq_length']
        n_samples = len(X)

        if n_samples <= seq_length:
            raise ValueError(f"样本数 {n_samples} 必须大于序列长度 {seq_length}")

        X_seq = []
        y_seq = []

        for i in range(seq_length, n_samples):
            X_seq.append(X[i-seq_length:i])
            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """训练模型"""
        logger.info("开始训练LSTM模型...")

        # 准备序列数据
        X_train_seq, y_train_seq = self.prepare_sequences(X_train, y_train)

        if X_val is not None and y_val is not None:
            X_val_seq, y_val_seq = self.prepare_sequences(X_val, y_val)
        else:
            X_val_seq, y_val_seq = None, None

        # 构建模型
        input_size = X_train_seq.shape[2]
        self.build(input_size)

        # 转换为Tensor
        X_train_tensor = torch.FloatTensor(X_train_seq).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train_seq).to(self.device)

        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.params['batch_size'],
            shuffle=True
        )

        if X_val_seq is not None:
            X_val_tensor = torch.FloatTensor(X_val_seq).to(self.device)
            y_val_tensor = torch.FloatTensor(y_val_seq).to(self.device)

        # 优化器和损失函数
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.params['learning_rate']
        )
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )

        # 训练循环
        best_val_loss = float('inf')
        patience_counter = 0
        self.training_history = []

        for epoch in range(self.params['epochs']):
            # 训练阶段
            self.model.train()
            train_loss = 0.0

            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)

            # 验证阶段
            val_loss = None
            if X_val_seq is not None:
                self.model.eval()
                with torch.no_grad():
                    val_outputs = self.model(X_val_tensor)
                    val_loss = criterion(val_outputs, y_val_tensor).item()

                scheduler.step(val_loss)

                # 早停检查
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    # 保存最佳模型
                    self.best_state = self.model.state_dict().copy()
                else:
                    patience_counter += 1

                if patience_counter >= self.params['early_stopping']:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

            # 记录历史
            history = {
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'lr': optimizer.param_groups[0]['lr']
            }
            self.training_history.append(history)

            if (epoch + 1) % 10 == 0:
                val_info = f", val_loss: {val_loss:.6f}" if val_loss else ""
                logger.info(
                    f"Epoch {epoch+1}/{self.params['epochs']} - "
                    f"train_loss: {train_loss:.6f}{val_info}"
                )

        # 恢复最佳模型
        if hasattr(self, 'best_state'):
            self.model.load_state_dict(self.best_state)

        self.is_fitted = True

        final_metrics = {
            'final_train_loss': self.training_history[-1]['train_loss'],
            'best_val_loss': best_val_loss if X_val_seq is not None else None,
            'epochs_trained': len(self.training_history)
        }

        logger.success(f"LSTM训练完成: {final_metrics}")
        return final_metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_fitted:
            raise ValueError("模型尚未训练")

        self.model.eval()

        # 准备序列 (使用0填充y)
        dummy_y = np.zeros(len(X))
        X_seq, _ = self.prepare_sequences(X, dummy_y)

        X_tensor = torch.FloatTensor(X_seq).to(self.device)

        with torch.no_grad():
            predictions = self.model(X_tensor).cpu().numpy()

        # 补充前seq_length个位置
        full_predictions = np.concatenate([
            np.full(self.params['seq_length'], np.nan),
            predictions
        ])

        return full_predictions

    def save(self, path: str) -> str:
        """保存模型 (包括PyTorch状态)"""
        import joblib

        save_path = f"{path}"

        # 保存PyTorch模型
        torch.save({
            'model_state_dict': self.model.state_dict() if self.model else None,
            'params': self.params,
            'name': self.name,
            'is_fitted': self.is_fitted,
            'training_history': self.training_history,
            'feature_names': self.feature_names
        }, save_path)

        logger.info(f"LSTM模型已保存: {save_path}")
        return save_path

    @classmethod
    def load(cls, path: str) -> 'LSTMModel':
        """加载模型"""
        checkpoint = torch.load(path, map_location='cpu')

        instance = cls(
            name=checkpoint['name'],
            params=checkpoint['params']
        )

        if checkpoint['model_state_dict'] is not None:
            # 需要知道input_size来重建模型
            # 这里假设从state_dict推断
            first_layer_weight = checkpoint['model_state_dict']['lstm.weight_ih_l0']
            input_size = first_layer_weight.shape[1]
            instance.build(input_size)
            instance.model.load_state_dict(checkpoint['model_state_dict'])

        instance.is_fitted = checkpoint['is_fitted']
        instance.training_history = checkpoint['training_history']
        instance.feature_names = checkpoint['feature_names']

        logger.info(f"LSTM模型已加载: {path}")
        return instance


if __name__ == "__main__":
    # 测试代码
    logger.info("测试LSTM模型")

    # 创建模拟数据
    np.random.seed(42)
    n_samples = 500
    n_features = 20

    X = np.random.randn(n_samples, n_features)
    y = np.sin(np.arange(n_samples) * 0.1) + np.random.randn(n_samples) * 0.1

    # 分割数据
    train_size = int(0.8 * n_samples)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    # 验证集
    val_size = int(0.2 * train_size)
    X_train, X_val = X_train[:-val_size], X_train[-val_size:]
    y_train, y_val = y_train[:-val_size], y_train[-val_size:]

    # 训练模型
    model = LSTMModel(
        name='test_lstm',
        params={
            'seq_length': 30,
            'hidden_size': 64,
            'num_layers': 2,
            'epochs': 20,
            'batch_size': 32
        }
    )

    metrics = model.fit(X_train, y_train, X_val, y_val)
    print(f"\n训练指标: {metrics}")

    # 预测
    predictions = model.predict(X_test)
    print(f"\n预测形状: {predictions.shape}")
    print(f"有效预测数: {np.sum(~np.isnan(predictions))}")

    # 评估
    valid_mask = ~np.isnan(predictions)
    eval_metrics = model.evaluate(
        X_test[valid_mask],
        y_test[valid_mask]
    )
    print(f"\n评估指标: {eval_metrics}")
