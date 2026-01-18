"""
特征选择模块
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from loguru import logger
from sklearn.feature_selection import (
    mutual_info_regression,
    VarianceThreshold,
    SelectKBest,
    f_regression
)
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class FeatureSelector:
    """特征选择类"""

    def __init__(self, df: pd.DataFrame, target_col: str = 'target'):
        """
        初始化

        Args:
            df: 包含特征的DataFrame
            target_col: 目标变量列名
        """
        self.df = df.copy()
        self.target_col = target_col
        self.selected_features: List[str] = []
        self.feature_importance: Dict[str, float] = {}

    def prepare_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """准备特征和目标变量"""
        # 排除非特征列
        exclude_cols = ['date', 'symbol', self.target_col]
        feature_cols = [col for col in self.df.columns if col not in exclude_cols]

        X = self.df[feature_cols].copy()
        y = self.df[self.target_col].copy() if self.target_col in self.df.columns else None

        # 处理无穷值
        X = X.replace([np.inf, -np.inf], np.nan)

        # 删除全为NaN的列
        X = X.dropna(axis=1, how='all')

        return X, y

    def correlation_filter(
        self,
        threshold: float = 0.95,
        method: str = 'pearson'
    ) -> List[str]:
        """
        基于相关性的特征过滤

        Args:
            threshold: 相关性阈值
            method: 相关性计算方法 ('pearson', 'spearman', 'kendall')

        Returns:
            保留的特征列表
        """
        X, _ = self.prepare_data()

        # 计算相关性矩阵
        corr_matrix = X.corr(method=method).abs()

        # 上三角矩阵
        upper = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # 找出高相关的特征
        to_drop = [col for col in upper.columns if any(upper[col] > threshold)]

        selected = [col for col in X.columns if col not in to_drop]

        logger.info(
            f"相关性过滤: 原始 {len(X.columns)} 列 → 保留 {len(selected)} 列 "
            f"(阈值={threshold})"
        )

        return selected

    def variance_filter(self, threshold: float = 0.01) -> List[str]:
        """
        基于方差的特征过滤

        Args:
            threshold: 方差阈值

        Returns:
            保留的特征列表
        """
        X, _ = self.prepare_data()

        # 填充缺失值
        X_filled = X.fillna(X.mean())

        # 标准化
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            scaler.fit_transform(X_filled),
            columns=X.columns
        )

        # 方差过滤
        selector = VarianceThreshold(threshold=threshold)
        selector.fit(X_scaled)

        selected = X.columns[selector.get_support()].tolist()

        logger.info(
            f"方差过滤: 原始 {len(X.columns)} 列 → 保留 {len(selected)} 列 "
            f"(阈值={threshold})"
        )

        return selected

    def mutual_information_selection(
        self,
        k: int = 50,
        target: Optional[pd.Series] = None
    ) -> List[str]:
        """
        基于互信息的特征选择

        Args:
            k: 选择的特征数量
            target: 目标变量 (可选)

        Returns:
            选中的特征列表
        """
        X, y = self.prepare_data()

        if y is None:
            if target is not None:
                y = target
            else:
                logger.error("未提供目标变量")
                return []

        # 对齐索引
        valid_idx = X.dropna().index.intersection(y.dropna().index)
        X_valid = X.loc[valid_idx].fillna(0)
        y_valid = y.loc[valid_idx]

        if len(X_valid) == 0:
            logger.error("没有有效数据")
            return []

        # 计算互信息
        mi_scores = mutual_info_regression(X_valid, y_valid, random_state=42)

        # 创建特征重要性字典
        feature_mi = dict(zip(X.columns, mi_scores))

        # 排序并选择top k
        sorted_features = sorted(feature_mi.items(), key=lambda x: x[1], reverse=True)
        selected = [f[0] for f in sorted_features[:k]]

        # 保存重要性
        self.feature_importance.update(feature_mi)

        logger.info(f"互信息选择: 选择 top {k} 特征")
        for i, (feat, score) in enumerate(sorted_features[:10]):
            logger.info(f"  {i+1}. {feat}: {score:.4f}")

        return selected

    def random_forest_importance(
        self,
        k: int = 50,
        target: Optional[pd.Series] = None,
        n_estimators: int = 100
    ) -> List[str]:
        """
        基于随机森林的特征重要性选择

        Args:
            k: 选择的特征数量
            target: 目标变量
            n_estimators: 树的数量

        Returns:
            选中的特征列表
        """
        X, y = self.prepare_data()

        if y is None:
            if target is not None:
                y = target
            else:
                logger.error("未提供目标变量")
                return []

        # 对齐和清洗
        valid_idx = X.dropna().index.intersection(y.dropna().index)
        X_valid = X.loc[valid_idx].fillna(0)
        y_valid = y.loc[valid_idx]

        if len(X_valid) < 100:
            logger.warning("样本量过少,随机森林特征选择可能不准确")

        # 训练随机森林
        rf = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_valid, y_valid)

        # 获取特征重要性
        feature_imp = dict(zip(X.columns, rf.feature_importances_))

        # 排序并选择top k
        sorted_features = sorted(feature_imp.items(), key=lambda x: x[1], reverse=True)
        selected = [f[0] for f in sorted_features[:k]]

        # 保存重要性
        self.feature_importance.update({f'rf_{k}': v for k, v in feature_imp.items()})

        logger.info(f"随机森林重要性选择: 选择 top {k} 特征")
        for i, (feat, score) in enumerate(sorted_features[:10]):
            logger.info(f"  {i+1}. {feat}: {score:.4f}")

        return selected

    def select_features(
        self,
        methods: List[str] = ['correlation', 'variance', 'importance'],
        correlation_threshold: float = 0.95,
        variance_threshold: float = 0.01,
        k_features: int = 50,
        target: Optional[pd.Series] = None
    ) -> List[str]:
        """
        综合特征选择流程

        Args:
            methods: 使用的方法列表
            correlation_threshold: 相关性阈值
            variance_threshold: 方差阈值
            k_features: 最终选择的特征数
            target: 目标变量

        Returns:
            最终选中的特征列表
        """
        X, y = self.prepare_data()
        if target is not None:
            y = target

        current_features = list(X.columns)
        logger.info(f"初始特征数: {len(current_features)}")

        # 1. 方差过滤
        if 'variance' in methods:
            variance_selected = self.variance_filter(variance_threshold)
            current_features = [f for f in current_features if f in variance_selected]
            logger.info(f"方差过滤后: {len(current_features)}")

        # 2. 相关性过滤
        if 'correlation' in methods:
            # 临时更新df只包含当前特征
            temp_df = self.df[current_features + [self.target_col] if self.target_col in self.df.columns else current_features].copy()
            temp_selector = FeatureSelector(temp_df, self.target_col)
            correlation_selected = temp_selector.correlation_filter(correlation_threshold)
            current_features = [f for f in current_features if f in correlation_selected]
            logger.info(f"相关性过滤后: {len(current_features)}")

        # 3. 基于重要性选择
        if 'importance' in methods and y is not None:
            # 临时更新df
            temp_df = self.df[current_features].copy()
            temp_df[self.target_col] = y

            temp_selector = FeatureSelector(temp_df, self.target_col)
            importance_selected = temp_selector.random_forest_importance(
                k=min(k_features, len(current_features)),
                target=y
            )
            current_features = [f for f in current_features if f in importance_selected]
            logger.info(f"重要性选择后: {len(current_features)}")

        self.selected_features = current_features

        logger.success(f"最终选择特征数: {len(self.selected_features)}")
        return self.selected_features

    def get_feature_importance_df(self) -> pd.DataFrame:
        """获取特征重要性DataFrame"""
        if not self.feature_importance:
            return pd.DataFrame()

        df = pd.DataFrame([
            {'feature': k, 'importance': v}
            for k, v in self.feature_importance.items()
        ])
        return df.sort_values('importance', ascending=False).reset_index(drop=True)


class FeaturePreprocessor:
    """特征预处理类"""

    @staticmethod
    def standardize(df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """标准化 (z-score)"""
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        result = df.copy()
        scaler = StandardScaler()

        for col in columns:
            if col in result.columns:
                valid_mask = result[col].notna()
                if valid_mask.any():
                    result.loc[valid_mask, col] = scaler.fit_transform(
                        result.loc[valid_mask, [col]]
                    )

        return result

    @staticmethod
    def normalize(df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """归一化到 [0, 1]"""
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        result = df.copy()

        for col in columns:
            if col in result.columns:
                min_val = result[col].min()
                max_val = result[col].max()
                if max_val > min_val:
                    result[col] = (result[col] - min_val) / (max_val - min_val)

        return result

    @staticmethod
    def winsorize(df: pd.DataFrame, columns: Optional[List[str]] = None,
                  lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
        """
        缩尾处理 (处理极端值)

        Args:
            df: 数据
            columns: 要处理的列
            lower: 下分位数
            upper: 上分位数
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        result = df.copy()

        for col in columns:
            if col in result.columns:
                lower_bound = result[col].quantile(lower)
                upper_bound = result[col].quantile(upper)
                result[col] = result[col].clip(lower=lower_bound, upper=upper_bound)

        return result

    @staticmethod
    def fill_missing(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
        """
        填充缺失值

        Args:
            df: 数据
            method: 'ffill', 'bfill', 'mean', 'median', 'zero'
        """
        result = df.copy()

        if method == 'ffill':
            result = result.fillna(method='ffill')
        elif method == 'bfill':
            result = result.fillna(method='bfill')
        elif method == 'mean':
            result = result.fillna(result.mean())
        elif method == 'median':
            result = result.fillna(result.median())
        elif method == 'zero':
            result = result.fillna(0)

        return result


if __name__ == "__main__":
    # 测试代码
    logger.info("测试特征选择模块")

    # 创建测试数据
    np.random.seed(42)
    n = 500

    # 模拟特征
    data = {
        f'feature_{i}': np.random.randn(n) for i in range(50)
    }

    # 添加一些高相关特征
    data['feature_corr1'] = data['feature_0'] + np.random.randn(n) * 0.1
    data['feature_corr2'] = data['feature_1'] + np.random.randn(n) * 0.1

    # 添加低方差特征
    data['feature_lowvar'] = np.ones(n) + np.random.randn(n) * 0.001

    # 目标变量 (与部分特征相关)
    data['target'] = (
        0.5 * data['feature_0'] +
        0.3 * data['feature_1'] +
        0.2 * data['feature_2'] +
        np.random.randn(n) * 0.1
    )

    df = pd.DataFrame(data)

    # 特征选择
    selector = FeatureSelector(df, target_col='target')

    # 测试各种方法
    print("\n=== 方差过滤 ===")
    var_selected = selector.variance_filter(threshold=0.01)
    print(f"选择的特征数: {len(var_selected)}")

    print("\n=== 相关性过滤 ===")
    corr_selected = selector.correlation_filter(threshold=0.95)
    print(f"选择的特征数: {len(corr_selected)}")

    print("\n=== 随机森林重要性 ===")
    rf_selected = selector.random_forest_importance(k=20)
    print(f"选择的特征数: {len(rf_selected)}")

    print("\n=== 综合特征选择 ===")
    final_selected = selector.select_features(
        methods=['variance', 'correlation', 'importance'],
        k_features=20
    )
    print(f"最终选择的特征: {final_selected}")
