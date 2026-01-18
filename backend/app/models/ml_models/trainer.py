"""
模型训练器 - 统一训练接口
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import optuna
from .base import BaseModel, ModelFactory


class ModelTrainer:
    """模型训练器"""

    def __init__(
        self,
        model: BaseModel,
        scaler: Optional[StandardScaler] = None
    ):
        """
        初始化

        Args:
            model: 模型实例
            scaler: 数据标准化器
        """
        self.model = model
        self.scaler = scaler or StandardScaler()
        self.training_results: Dict[str, Any] = {}

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        准备训练数据

        Args:
            df: 数据
            feature_cols: 特征列
            target_col: 目标列
            train_ratio: 训练集比例
            val_ratio: 验证集比例

        Returns:
            X_train, y_train, X_val, y_val, X_test, y_test
        """
        # 删除NaN
        valid_df = df[feature_cols + [target_col]].dropna()

        X = valid_df[feature_cols].values
        y = valid_df[target_col].values

        n_samples = len(X)
        train_end = int(n_samples * train_ratio)
        val_end = int(n_samples * (train_ratio + val_ratio))

        X_train = X[:train_end]
        y_train = y[:train_end]
        X_val = X[train_end:val_end]
        y_val = y[train_end:val_end]
        X_test = X[val_end:]
        y_test = y[val_end:]

        # 标准化
        X_train = self.scaler.fit_transform(X_train)
        X_val = self.scaler.transform(X_val)
        X_test = self.scaler.transform(X_test)

        # 保存特征名
        self.model.feature_names = feature_cols

        logger.info(
            f"数据准备完成: "
            f"train={len(X_train)}, val={len(X_val)}, test={len(X_test)}"
        )

        return X_train, y_train, X_val, y_val, X_test, y_test

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """训练模型"""
        metrics = self.model.fit(X_train, y_train, X_val, y_val)
        self.training_results['train_metrics'] = metrics
        return metrics

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """评估模型"""
        metrics = self.model.evaluate(X_test, y_test)
        self.training_results['test_metrics'] = metrics
        return metrics

    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5
    ) -> Dict[str, List[float]]:
        """
        时间序列交叉验证

        Args:
            X: 特征
            y: 目标
            n_splits: 折数

        Returns:
            每折的评估指标
        """
        logger.info(f"开始{n_splits}折时间序列交叉验证...")

        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_results = {
            'rmse': [],
            'mae': [],
            'r2': [],
            'direction_accuracy': []
        }

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            logger.info(f"训练第 {fold+1}/{n_splits} 折...")

            X_train_fold = X[train_idx]
            y_train_fold = y[train_idx]
            X_val_fold = X[val_idx]
            y_val_fold = y[val_idx]

            # 创建新模型实例
            fold_model = ModelFactory.create(
                name=f"{self.model.name}_fold{fold}",
                model_type=self.model.__class__.__name__.lower().replace('model', ''),
                params=self.model.params
            )

            # 训练
            fold_model.fit(X_train_fold, y_train_fold)

            # 评估
            metrics = fold_model.evaluate(X_val_fold, y_val_fold)

            for key in cv_results:
                if key in metrics:
                    cv_results[key].append(metrics[key])

        # 计算平均值和标准差
        cv_summary = {}
        for key, values in cv_results.items():
            if values:
                cv_summary[f'{key}_mean'] = np.mean(values)
                cv_summary[f'{key}_std'] = np.std(values)

        self.training_results['cv_results'] = cv_results
        self.training_results['cv_summary'] = cv_summary

        logger.success(f"交叉验证完成: RMSE={cv_summary.get('rmse_mean', 0):.4f} "
                      f"(±{cv_summary.get('rmse_std', 0):.4f})")

        return cv_results


class HyperparameterTuner:
    """超参数优化器"""

    def __init__(
        self,
        model_type: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ):
        """
        初始化

        Args:
            model_type: 模型类型
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
        """
        self.model_type = model_type
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.best_params: Dict[str, Any] = {}
        self.study: Optional[optuna.Study] = None

    def _get_param_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """定义参数搜索空间"""
        if self.model_type == 'lightgbm':
            return {
                'num_leaves': trial.suggest_int('num_leaves', 20, 100),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
                'max_depth': trial.suggest_int('max_depth', 3, 15),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            }
        elif self.model_type == 'xgboost':
            return {
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            }
        elif self.model_type == 'lstm':
            return {
                'hidden_size': trial.suggest_categorical('hidden_size', [64, 128, 256]),
                'num_layers': trial.suggest_int('num_layers', 1, 3),
                'dropout': trial.suggest_float('dropout', 0.1, 0.5),
                'learning_rate': trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True),
                'batch_size': trial.suggest_categorical('batch_size', [32, 64, 128]),
            }
        else:
            return {}

    def _objective(self, trial: optuna.Trial) -> float:
        """优化目标函数"""
        params = self._get_param_space(trial)

        model = ModelFactory.create(
            name=f"optuna_trial_{trial.number}",
            model_type=self.model_type,
            params=params
        )

        model.fit(self.X_train, self.y_train, self.X_val, self.y_val)
        metrics = model.evaluate(self.X_val, self.y_val)

        return metrics['rmse']

    def optimize(
        self,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        n_jobs: int = 1
    ) -> Dict[str, Any]:
        """
        执行超参数优化

        Args:
            n_trials: 试验次数
            timeout: 超时时间(秒)
            n_jobs: 并行任务数

        Returns:
            最佳参数
        """
        logger.info(f"开始超参数优化: {self.model_type}, n_trials={n_trials}")

        self.study = optuna.create_study(
            direction='minimize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )

        self.study.optimize(
            self._objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=n_jobs,
            show_progress_bar=True
        )

        self.best_params = self.study.best_params

        logger.success(
            f"超参数优化完成: "
            f"best_rmse={self.study.best_value:.4f}, "
            f"best_params={self.best_params}"
        )

        return self.best_params

    def get_optimization_history(self) -> pd.DataFrame:
        """获取优化历史"""
        if self.study is None:
            return pd.DataFrame()

        return self.study.trials_dataframe()


class EnsembleModel:
    """模型集成"""

    def __init__(
        self,
        models: List[BaseModel],
        weights: Optional[List[float]] = None
    ):
        """
        初始化

        Args:
            models: 模型列表
            weights: 权重列表
        """
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)

        if len(self.weights) != len(self.models):
            raise ValueError("权重数量必须与模型数量相同")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """加权平均预测"""
        predictions = []

        for model in self.models:
            pred = model.predict(X)
            predictions.append(pred)

        # 加权平均
        weighted_sum = np.zeros_like(predictions[0])
        for pred, weight in zip(predictions, self.weights):
            # 处理NaN
            valid_mask = ~np.isnan(pred)
            weighted_sum[valid_mask] += pred[valid_mask] * weight

        return weighted_sum

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """评估集成模型"""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        predictions = self.predict(X)

        # 过滤NaN
        valid_mask = ~np.isnan(predictions)
        y_valid = y[valid_mask]
        pred_valid = predictions[valid_mask]

        return {
            'rmse': np.sqrt(mean_squared_error(y_valid, pred_valid)),
            'mae': mean_absolute_error(y_valid, pred_valid),
            'r2': r2_score(y_valid, pred_valid)
        }


if __name__ == "__main__":
    # 测试代码
    logger.info("测试模型训练器")

    from .gradient_boosting import LightGBMModel, XGBoostModel

    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = np.random.randn(n_samples, n_features)
    y = 0.5 * X[:, 0] + 0.3 * X[:, 1] + np.random.randn(n_samples) * 0.1

    # 创建模型
    lgb_model = LightGBMModel(name='trainer_test')
    trainer = ModelTrainer(lgb_model)

    # 准备数据
    df = pd.DataFrame(X, columns=[f'f_{i}' for i in range(n_features)])
    df['target'] = y

    X_train, y_train, X_val, y_val, X_test, y_test = trainer.prepare_data(
        df,
        feature_cols=[f'f_{i}' for i in range(n_features)],
        target_col='target'
    )

    # 训练
    train_metrics = trainer.train(X_train, y_train, X_val, y_val)
    print(f"\n训练指标: {train_metrics}")

    # 评估
    test_metrics = trainer.evaluate(X_test, y_test)
    print(f"测试指标: {test_metrics}")

    # 交叉验证
    cv_results = trainer.cross_validate(
        np.vstack([X_train, X_val]),
        np.concatenate([y_train, y_val]),
        n_splits=3
    )
    print(f"\n交叉验证结果: {trainer.training_results['cv_summary']}")
