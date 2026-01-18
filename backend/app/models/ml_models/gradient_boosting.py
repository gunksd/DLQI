"""
LightGBM梯度提升模型
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
import lightgbm as lgb
from .base import BaseModel, register_model


@register_model('lightgbm')
class LightGBMModel(BaseModel):
    """LightGBM预测模型"""

    def __init__(self, name: str = 'lightgbm', params: Optional[Dict] = None):
        default_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'max_depth': -1,
            'min_child_samples': 20,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'n_estimators': 1000,
            'early_stopping_rounds': 50,
            'verbose': -1
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def build(self):
        """构建模型 (LightGBM在fit时自动构建)"""
        logger.info("LightGBM模型将在训练时构建")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """训练模型"""
        logger.info("开始训练LightGBM模型...")

        # 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train)

        valid_sets = [train_data]
        valid_names = ['train']

        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)
            valid_names.append('valid')

        # 提取训练参数
        train_params = {k: v for k, v in self.params.items()
                       if k not in ['n_estimators', 'early_stopping_rounds']}

        # 记录训练过程
        evals_result = {}
        callbacks = [
            lgb.record_evaluation(evals_result),
            lgb.log_evaluation(period=100)
        ]

        if self.params['early_stopping_rounds'] and X_val is not None:
            callbacks.append(
                lgb.early_stopping(
                    stopping_rounds=self.params['early_stopping_rounds'],
                    verbose=False
                )
            )

        # 训练模型
        self.model = lgb.train(
            train_params,
            train_data,
            num_boost_round=self.params['n_estimators'],
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )

        self.is_fitted = True

        # 记录训练历史
        for i in range(len(evals_result['train'][self.params['metric']])):
            history = {
                'iteration': i + 1,
                'train_loss': evals_result['train'][self.params['metric']][i]
            }
            if 'valid' in evals_result:
                history['val_loss'] = evals_result['valid'][self.params['metric']][i]
            self.training_history.append(history)

        # 最终指标
        final_metrics = {
            'best_iteration': self.model.best_iteration,
            'train_rmse': evals_result['train'][self.params['metric']][-1]
        }

        if 'valid' in evals_result:
            final_metrics['val_rmse'] = evals_result['valid'][self.params['metric']][-1]
            final_metrics['best_val_rmse'] = min(evals_result['valid'][self.params['metric']])

        logger.success(f"LightGBM训练完成: {final_metrics}")
        return final_metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_fitted:
            raise ValueError("模型尚未训练")

        predictions = self.model.predict(X, num_iteration=self.model.best_iteration)
        return predictions

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """获取特征重要性"""
        if not self.is_fitted:
            return None

        importance = self.model.feature_importance(importance_type='gain')

        if self.feature_names:
            return dict(zip(self.feature_names, importance))
        else:
            return {f'feature_{i}': imp for i, imp in enumerate(importance)}

    def get_feature_importance_df(self) -> pd.DataFrame:
        """获取特征重要性DataFrame"""
        importance_dict = self.get_feature_importance()
        if not importance_dict:
            return pd.DataFrame()

        df = pd.DataFrame([
            {'feature': k, 'importance': v}
            for k, v in importance_dict.items()
        ])
        return df.sort_values('importance', ascending=False).reset_index(drop=True)


@register_model('xgboost')
class XGBoostModel(BaseModel):
    """XGBoost预测模型"""

    def __init__(self, name: str = 'xgboost', params: Optional[Dict] = None):
        default_params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'booster': 'gbtree',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 1000,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'min_child_weight': 3,
            'gamma': 0.1,
            'early_stopping_rounds': 50,
            'verbosity': 0
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def build(self):
        """构建模型"""
        import xgboost as xgb
        logger.info("XGBoost模型将在训练时构建")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """训练模型"""
        import xgboost as xgb

        logger.info("开始训练XGBoost模型...")

        # 提取参数
        xgb_params = {k: v for k, v in self.params.items()
                     if k not in ['n_estimators', 'early_stopping_rounds']}

        # 创建模型
        self.model = xgb.XGBRegressor(
            n_estimators=self.params['n_estimators'],
            early_stopping_rounds=self.params['early_stopping_rounds'] if X_val is not None else None,
            **xgb_params
        )

        # 训练
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=False
        )

        self.is_fitted = True

        # 评估结果
        evals_result = self.model.evals_result()

        # 记录训练历史
        train_key = 'validation_0'
        val_key = 'validation_1' if X_val is not None else None

        for i in range(len(evals_result[train_key]['rmse'])):
            history = {
                'iteration': i + 1,
                'train_loss': evals_result[train_key]['rmse'][i]
            }
            if val_key:
                history['val_loss'] = evals_result[val_key]['rmse'][i]
            self.training_history.append(history)

        # 最终指标
        final_metrics = {
            'best_iteration': self.model.best_iteration,
            'train_rmse': evals_result[train_key]['rmse'][-1]
        }

        if val_key:
            final_metrics['val_rmse'] = evals_result[val_key]['rmse'][-1]
            final_metrics['best_val_rmse'] = min(evals_result[val_key]['rmse'])

        logger.success(f"XGBoost训练完成: {final_metrics}")
        return final_metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_fitted:
            raise ValueError("模型尚未训练")

        return self.model.predict(X)

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """获取特征重要性"""
        if not self.is_fitted:
            return None

        importance = self.model.feature_importances_

        if self.feature_names:
            return dict(zip(self.feature_names, importance))
        else:
            return {f'feature_{i}': imp for i, imp in enumerate(importance)}


@register_model('random_forest')
class RandomForestModel(BaseModel):
    """随机森林预测模型"""

    def __init__(self, name: str = 'random_forest', params: Optional[Dict] = None):
        default_params = {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'bootstrap': True,
            'n_jobs': -1,
            'random_state': 42
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def build(self):
        """构建模型"""
        from sklearn.ensemble import RandomForestRegressor
        self.model = RandomForestRegressor(**self.params)
        logger.info("随机森林模型已构建")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """训练模型"""
        logger.info("开始训练随机森林模型...")

        self.build()
        self.model.fit(X_train, y_train)
        self.is_fitted = True

        # 计算指标
        from sklearn.metrics import mean_squared_error

        train_pred = self.model.predict(X_train)
        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))

        final_metrics = {
            'train_rmse': train_rmse,
            'n_estimators': self.params['n_estimators']
        }

        if X_val is not None and y_val is not None:
            val_pred = self.model.predict(X_val)
            val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
            final_metrics['val_rmse'] = val_rmse

        logger.success(f"随机森林训练完成: {final_metrics}")
        return final_metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_fitted:
            raise ValueError("模型尚未训练")

        return self.model.predict(X)

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """获取特征重要性"""
        if not self.is_fitted:
            return None

        importance = self.model.feature_importances_

        if self.feature_names:
            return dict(zip(self.feature_names, importance))
        else:
            return {f'feature_{i}': imp for i, imp in enumerate(importance)}


if __name__ == "__main__":
    # 测试代码
    logger.info("测试梯度提升模型")

    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = np.random.randn(n_samples, n_features)
    y = 0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 2] + np.random.randn(n_samples) * 0.1

    # 分割数据
    train_size = int(0.7 * n_samples)
    val_size = int(0.15 * n_samples)

    X_train = X[:train_size]
    y_train = y[:train_size]
    X_val = X[train_size:train_size+val_size]
    y_val = y[train_size:train_size+val_size]
    X_test = X[train_size+val_size:]
    y_test = y[train_size+val_size:]

    # 测试LightGBM
    print("\n=== LightGBM ===")
    lgb_model = LightGBMModel(name='test_lgb')
    lgb_metrics = lgb_model.fit(X_train, y_train, X_val, y_val)
    lgb_eval = lgb_model.evaluate(X_test, y_test)
    print(f"测试指标: {lgb_eval}")

    # 特征重要性
    importance = lgb_model.get_feature_importance()
    print(f"Top 5 特征重要性: {dict(list(sorted(importance.items(), key=lambda x: -x[1]))[:5])}")

    # 测试XGBoost
    print("\n=== XGBoost ===")
    xgb_model = XGBoostModel(name='test_xgb')
    xgb_metrics = xgb_model.fit(X_train, y_train, X_val, y_val)
    xgb_eval = xgb_model.evaluate(X_test, y_test)
    print(f"测试指标: {xgb_eval}")

    # 测试随机森林
    print("\n=== 随机森林 ===")
    rf_model = RandomForestModel(name='test_rf', params={'n_estimators': 100})
    rf_metrics = rf_model.fit(X_train, y_train, X_val, y_val)
    rf_eval = rf_model.evaluate(X_test, y_test)
    print(f"测试指标: {rf_eval}")
