"""
模型基类和工厂类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from datetime import datetime
from loguru import logger


class BaseModel(ABC):
    """机器学习模型基类"""

    def __init__(self, name: str, params: Optional[Dict] = None):
        """
        初始化

        Args:
            name: 模型名称
            params: 模型参数
        """
        self.name = name
        self.params = params or {}
        self.model = None
        self.is_fitted = False
        self.training_history: List[Dict] = []
        self.feature_names: List[str] = []

    @abstractmethod
    def build(self):
        """构建模型"""
        pass

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        训练模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签

        Returns:
            训练指标字典
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测

        Args:
            X: 特征

        Returns:
            预测结果
        """
        pass

    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Dict[str, float]:
        """
        评估模型

        Args:
            X: 特征
            y: 真实标签

        Returns:
            评估指标
        """
        from sklearn.metrics import (
            mean_squared_error,
            mean_absolute_error,
            r2_score
        )

        predictions = self.predict(X)

        mse = mean_squared_error(y, predictions)
        mae = mean_absolute_error(y, predictions)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, predictions)

        # 方向准确率
        if len(y) > 1:
            direction_acc = np.mean(np.sign(predictions[1:]) == np.sign(y[1:]))
        else:
            direction_acc = 0.0

        metrics = {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'direction_accuracy': direction_acc
        }

        return metrics

    def save(self, path: str) -> str:
        """
        保存模型

        Args:
            path: 保存路径

        Returns:
            保存的文件路径
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            'name': self.name,
            'params': self.params,
            'model': self.model,
            'is_fitted': self.is_fitted,
            'training_history': self.training_history,
            'feature_names': self.feature_names,
            'saved_at': datetime.now().isoformat()
        }

        joblib.dump(model_data, save_path)
        logger.info(f"模型已保存: {save_path}")
        return str(save_path)

    @classmethod
    def load(cls, path: str) -> 'BaseModel':
        """
        加载模型

        Args:
            path: 模型路径

        Returns:
            模型实例
        """
        model_data = joblib.load(path)

        instance = cls(
            name=model_data['name'],
            params=model_data['params']
        )
        instance.model = model_data['model']
        instance.is_fitted = model_data['is_fitted']
        instance.training_history = model_data['training_history']
        instance.feature_names = model_data['feature_names']

        logger.info(f"模型已加载: {path}")
        return instance

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """获取特征重要性"""
        return None

    def summary(self) -> Dict[str, Any]:
        """模型摘要"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'params': self.params,
            'is_fitted': self.is_fitted,
            'n_features': len(self.feature_names),
            'training_epochs': len(self.training_history)
        }


class ModelFactory:
    """模型工厂类"""

    _models = {}

    @classmethod
    def register(cls, name: str, model_class: type):
        """注册模型类"""
        cls._models[name] = model_class
        logger.debug(f"注册模型: {name}")

    @classmethod
    def create(
        cls,
        name: str,
        model_type: str,
        params: Optional[Dict] = None
    ) -> BaseModel:
        """
        创建模型实例

        Args:
            name: 模型名称
            model_type: 模型类型
            params: 模型参数

        Returns:
            模型实例
        """
        if model_type not in cls._models:
            raise ValueError(f"未知模型类型: {model_type}. 可用类型: {list(cls._models.keys())}")

        model_class = cls._models[model_type]
        return model_class(name=name, params=params)

    @classmethod
    def list_models(cls) -> List[str]:
        """列出所有可用模型类型"""
        return list(cls._models.keys())


def register_model(name: str):
    """模型注册装饰器"""
    def decorator(cls):
        ModelFactory.register(name, cls)
        return cls
    return decorator
