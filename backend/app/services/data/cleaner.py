"""
数据清洗模块
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from loguru import logger
from scipy import stats


class DataCleaner:
    """数据清洗类"""

    def __init__(self, verbose: bool = True):
        """
        初始化数据清洗器

        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose

    def clean_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        完整的数据清洗流程

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        if df.empty:
            logger.warning("输入数据为空")
            return df

        original_len = len(df)
        logger.info(f"开始清洗数据,原始数据: {original_len} 行")

        # 1. 排序和去重
        df = self.sort_and_deduplicate(df)

        # 2. 处理缺失值
        df = self.handle_missing_values(df)

        # 3. 检测异常值
        df = self.detect_and_handle_outliers(df)

        # 4. 修正价格逻辑错误
        df = self.fix_price_logic(df)

        # 5. 重置索引
        df = df.reset_index(drop=True)

        cleaned_len = len(df)
        removed = original_len - cleaned_len
        logger.success(
            f"数据清洗完成,保留: {cleaned_len} 行, 移除: {removed} 行 "
            f"({removed/original_len*100:.2f}%)"
        )

        return df

    def sort_and_deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """排序并去重"""
        # 按日期排序
        df = df.sort_values('date').copy()

        # 去除重复日期(保留第一条)
        duplicates = df['date'].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"发现 {duplicates} 个重复日期,已去除")
            df = df.drop_duplicates(subset=['date'], keep='first')

        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        if df.empty:
            return df

        # 检查缺失值
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()

        if total_nulls == 0:
            logger.info("无缺失值")
            return df

        logger.warning(f"发现缺失值: {total_nulls} 个")

        # 对于价格列,使用前向填充
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns and df[col].isnull().any():
                before = df[col].isnull().sum()
                df[col] = df[col].fillna(method='ffill')  # 前向填充
                df[col] = df[col].fillna(method='bfill')  # 后向填充(首行)
                after = df[col].isnull().sum()
                logger.info(f"{col}: 填充 {before - after} 个缺失值")

        # 对于成交量,使用0填充
        if 'volume' in df.columns:
            before = df['volume'].isnull().sum()
            df['volume'] = df['volume'].fillna(0)
            if before > 0:
                logger.info(f"volume: 填充 {before} 个缺失值(使用0)")

        # 删除仍有缺失值的行
        remaining_nulls = df.isnull().sum().sum()
        if remaining_nulls > 0:
            df = df.dropna()
            logger.warning(f"删除 {remaining_nulls} 行无法填充的数据")

        return df

    def detect_and_handle_outliers(
        self,
        df: pd.DataFrame,
        method: str = "iqr",
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        检测和处理异常值

        Args:
            df: 数据
            method: 'iqr' 或 'zscore'
            threshold: 异常值阈值

        Returns:
            处理后的数据
        """
        if df.empty:
            return df

        price_columns = ['open', 'high', 'low', 'close']
        outlier_mask = pd.Series([False] * len(df), index=df.index)

        for col in price_columns:
            if col not in df.columns:
                continue

            if method == "iqr":
                # IQR方法
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                col_outliers = (df[col] < lower_bound) | (df[col] > upper_bound)

            elif method == "zscore":
                # Z-score方法
                z_scores = np.abs(stats.zscore(df[col]))
                col_outliers = z_scores > threshold

            else:
                raise ValueError(f"不支持的方法: {method}")

            outlier_mask |= col_outliers

            if col_outliers.any():
                count = col_outliers.sum()
                logger.warning(f"{col}: 发现 {count} 个异常值")

        # 删除异常值
        total_outliers = outlier_mask.sum()
        if total_outliers > 0:
            df = df[~outlier_mask].copy()
            logger.warning(f"共删除 {total_outliers} 行异常数据")

        return df

    def fix_price_logic(self, df: pd.DataFrame) -> pd.DataFrame:
        """修正价格逻辑错误"""
        if df.empty or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            return df

        errors_found = 0

        # High应该是最高价
        mask = df['high'] < df[['open', 'low', 'close']].max(axis=1)
        if mask.any():
            count = mask.sum()
            df.loc[mask, 'high'] = df.loc[mask, ['open', 'low', 'close']].max(axis=1)
            errors_found += count
            logger.warning(f"修正 {count} 个high价格错误")

        # Low应该是最低价
        mask = df['low'] > df[['open', 'high', 'close']].min(axis=1)
        if mask.any():
            count = mask.sum()
            df.loc[mask, 'low'] = df.loc[mask, ['open', 'high', 'close']].min(axis=1)
            errors_found += count
            logger.warning(f"修正 {count} 个low价格错误")

        if errors_found == 0:
            logger.info("价格逻辑检查通过")

        return df

    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算收益率"""
        if 'close' not in df.columns:
            return df

        # 简单收益率
        df['returns'] = df['close'].pct_change()

        # 对数收益率
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # 累计收益
        df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1

        logger.info("收益率计算完成")
        return df

    def align_timestamps(self, dfs: dict) -> dict:
        """
        对齐多个DataFrame的时间戳

        Args:
            dfs: {symbol: DataFrame} 字典

        Returns:
            对齐后的字典
        """
        if not dfs:
            return dfs

        # 找到公共日期
        dates = None
        for symbol, df in dfs.items():
            current_dates = set(df['date'])
            dates = current_dates if dates is None else dates.intersection(current_dates)

        common_dates = sorted(dates)
        logger.info(f"公共日期数量: {len(common_dates)}")

        # 过滤到公共日期
        aligned_dfs = {}
        for symbol, df in dfs.items():
            aligned_df = df[df['date'].isin(common_dates)].copy()
            aligned_dfs[symbol] = aligned_df
            logger.info(f"{symbol}: {len(df)} → {len(aligned_df)} 行")

        return aligned_dfs


class DataAugmentor:
    """数据增强类"""

    @staticmethod
    def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
        """添加基础特征"""
        if df.empty:
            return df

        # 价格变化
        df['price_change'] = df['close'] - df['open']
        df['price_amplitude'] = df['high'] - df['low']

        # 成交量变化
        if 'volume' in df.columns:
            df['volume_change'] = df['volume'].pct_change()

        # 日期特征
        df['year'] = pd.to_datetime(df['date']).dt.year
        df['month'] = pd.to_datetime(df['date']).dt.month
        df['day'] = pd.to_datetime(df['date']).dt.day
        df['dayofweek'] = pd.to_datetime(df['date']).dt.dayofweek

        logger.info("基础特征添加完成")
        return df


if __name__ == "__main__":
    # 测试代码
    logger.info("测试数据清洗模块")

    # 创建测试数据
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100)
    })

    # 人为添加一些问题
    test_data.loc[10, 'close'] = np.nan  # 缺失值
    test_data.loc[20, 'high'] = test_data.loc[20, 'low'] - 5  # 逻辑错误
    test_data.loc[30, 'close'] = 1000  # 异常值

    print("=== 原始数据 ===")
    print(test_data.describe())

    # 清洗数据
    cleaner = DataCleaner()
    cleaned_data = cleaner.clean_pipeline(test_data)

    print("\n=== 清洗后数据 ===")
    print(cleaned_data.describe())

    # 添加收益率
    cleaned_data = cleaner.calculate_returns(cleaned_data)
    print("\n=== 收益率统计 ===")
    print(cleaned_data[['returns', 'log_returns', 'cumulative_returns']].describe())
