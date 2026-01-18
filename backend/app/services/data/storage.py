"""
数据存储模块 - 支持多种存储后端
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Union
from datetime import datetime
import json
import h5py
from loguru import logger


class DataStorage:
    """数据存储管理类"""

    def __init__(self, base_path: str = "data"):
        """
        初始化存储管理器

        Args:
            base_path: 数据存储根目录
        """
        self.base_path = Path(base_path)
        self._ensure_directories()
        logger.info(f"初始化数据存储: {self.base_path}")

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = ['raw', 'processed', 'features', 'models', 'backtest_results']
        for dir_name in directories:
            (self.base_path / dir_name).mkdir(parents=True, exist_ok=True)

    # ==================== CSV存储 ====================

    def save_to_csv(
        self,
        df: pd.DataFrame,
        filename: str,
        subdir: str = "raw"
    ) -> str:
        """
        保存DataFrame到CSV文件

        Args:
            df: 数据
            filename: 文件名(不含扩展名)
            subdir: 子目录

        Returns:
            保存的文件路径
        """
        if not filename.endswith('.csv'):
            filename = f"{filename}.csv"

        filepath = self.base_path / subdir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"数据已保存到CSV: {filepath}")
        return str(filepath)

    def load_from_csv(
        self,
        filename: str,
        subdir: str = "raw",
        parse_dates: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        从CSV文件加载数据

        Args:
            filename: 文件名
            subdir: 子目录
            parse_dates: 需要解析为日期的列

        Returns:
            DataFrame
        """
        if not filename.endswith('.csv'):
            filename = f"{filename}.csv"

        filepath = self.base_path / subdir / filename

        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            return pd.DataFrame()

        df = pd.read_csv(filepath, parse_dates=parse_dates or ['date'])
        logger.info(f"从CSV加载数据: {filepath}, {len(df)} 行")
        return df

    # ==================== HDF5存储 ====================

    def save_to_hdf5(
        self,
        df: pd.DataFrame,
        symbol: str,
        data_type: str = "market_data"
    ) -> str:
        """
        保存DataFrame到HDF5文件(高效存储大量时间序列)

        Args:
            df: 数据
            symbol: 股票代码
            data_type: 数据类型 (market_data, features, predictions)

        Returns:
            保存的文件路径
        """
        filepath = self.base_path / "processed" / f"{data_type}.h5"

        # 使用pandas的HDF5接口
        key = f"/{data_type}/{symbol.replace('.', '_')}"

        df.to_hdf(
            filepath,
            key=key,
            mode='a',
            format='table',
            data_columns=True,
            complevel=9,
            complib='blosc'
        )

        logger.info(f"数据已保存到HDF5: {filepath}, key={key}")
        return str(filepath)

    def load_from_hdf5(
        self,
        symbol: str,
        data_type: str = "market_data",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        从HDF5文件加载数据

        Args:
            symbol: 股票代码
            data_type: 数据类型
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            DataFrame
        """
        filepath = self.base_path / "processed" / f"{data_type}.h5"

        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            return pd.DataFrame()

        key = f"/{data_type}/{symbol.replace('.', '_')}"

        try:
            # 构建查询条件
            where = None
            if start_date and end_date:
                where = f"date >= '{start_date}' & date <= '{end_date}'"
            elif start_date:
                where = f"date >= '{start_date}'"
            elif end_date:
                where = f"date <= '{end_date}'"

            df = pd.read_hdf(filepath, key=key, where=where)
            logger.info(f"从HDF5加载数据: {key}, {len(df)} 行")
            return df

        except KeyError:
            logger.error(f"HDF5中不存在key: {key}")
            return pd.DataFrame()

    def list_hdf5_keys(self, data_type: str = "market_data") -> List[str]:
        """列出HDF5文件中的所有key"""
        filepath = self.base_path / "processed" / f"{data_type}.h5"

        if not filepath.exists():
            return []

        with pd.HDFStore(filepath, mode='r') as store:
            keys = store.keys()

        return keys

    # ==================== Parquet存储 ====================

    def save_to_parquet(
        self,
        df: pd.DataFrame,
        filename: str,
        subdir: str = "processed"
    ) -> str:
        """
        保存DataFrame到Parquet文件(列式存储,高压缩比)

        Args:
            df: 数据
            filename: 文件名
            subdir: 子目录

        Returns:
            保存的文件路径
        """
        if not filename.endswith('.parquet'):
            filename = f"{filename}.parquet"

        filepath = self.base_path / subdir / filename
        df.to_parquet(filepath, index=False, compression='snappy')
        logger.info(f"数据已保存到Parquet: {filepath}")
        return str(filepath)

    def load_from_parquet(
        self,
        filename: str,
        subdir: str = "processed",
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        从Parquet文件加载数据

        Args:
            filename: 文件名
            subdir: 子目录
            columns: 需要加载的列

        Returns:
            DataFrame
        """
        if not filename.endswith('.parquet'):
            filename = f"{filename}.parquet"

        filepath = self.base_path / subdir / filename

        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            return pd.DataFrame()

        df = pd.read_parquet(filepath, columns=columns)
        logger.info(f"从Parquet加载数据: {filepath}, {len(df)} 行")
        return df

    # ==================== 批量操作 ====================

    def save_multiple(
        self,
        data_dict: Dict[str, pd.DataFrame],
        format: str = "csv",
        subdir: str = "raw"
    ) -> Dict[str, str]:
        """
        批量保存多个DataFrame

        Args:
            data_dict: {symbol: DataFrame}
            format: 存储格式 ('csv', 'parquet', 'hdf5')
            subdir: 子目录

        Returns:
            {symbol: filepath}
        """
        results = {}

        for symbol, df in data_dict.items():
            if format == "csv":
                path = self.save_to_csv(df, symbol, subdir)
            elif format == "parquet":
                path = self.save_to_parquet(df, symbol, subdir)
            elif format == "hdf5":
                path = self.save_to_hdf5(df, symbol)
            else:
                raise ValueError(f"不支持的格式: {format}")

            results[symbol] = path

        logger.success(f"批量保存完成: {len(results)} 个文件")
        return results

    def list_files(
        self,
        subdir: str = "raw",
        pattern: str = "*"
    ) -> List[str]:
        """列出目录下的文件"""
        dir_path = self.base_path / subdir
        files = list(dir_path.glob(pattern))
        return [str(f) for f in files]

    # ==================== 元数据管理 ====================

    def save_metadata(self, metadata: Dict, name: str) -> str:
        """保存元数据到JSON"""
        filepath = self.base_path / "metadata" / f"{name}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"元数据已保存: {filepath}")
        return str(filepath)

    def load_metadata(self, name: str) -> Dict:
        """加载元数据"""
        filepath = self.base_path / "metadata" / f"{name}.json"

        if not filepath.exists():
            logger.warning(f"元数据不存在: {filepath}")
            return {}

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ==================== 数据统计 ====================

    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        stats = {}

        for subdir in ['raw', 'processed', 'features', 'models']:
            dir_path = self.base_path / subdir
            if dir_path.exists():
                files = list(dir_path.glob('*'))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                stats[subdir] = {
                    'file_count': len(files),
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                }

        return stats


class DataCache:
    """内存缓存管理"""

    def __init__(self, max_size: int = 100):
        """
        初始化缓存

        Args:
            max_size: 最大缓存数量
        """
        self.max_size = max_size
        self._cache: Dict[str, pd.DataFrame] = {}
        self._access_times: Dict[str, datetime] = {}

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """获取缓存数据"""
        if key in self._cache:
            self._access_times[key] = datetime.now()
            logger.debug(f"缓存命中: {key}")
            return self._cache[key].copy()
        logger.debug(f"缓存未命中: {key}")
        return None

    def set(self, key: str, df: pd.DataFrame):
        """设置缓存数据"""
        # 检查是否需要清理
        if len(self._cache) >= self.max_size:
            self._evict()

        self._cache[key] = df.copy()
        self._access_times[key] = datetime.now()
        logger.debug(f"数据已缓存: {key}")

    def _evict(self):
        """LRU淘汰策略"""
        if not self._access_times:
            return

        # 找到最久未访问的key
        oldest_key = min(self._access_times, key=self._access_times.get)
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
        logger.debug(f"缓存淘汰: {oldest_key}")

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_times.clear()
        logger.info("缓存已清空")

    def stats(self) -> Dict:
        """获取缓存统计"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'keys': list(self._cache.keys())
        }


if __name__ == "__main__":
    # 测试代码
    logger.info("测试数据存储模块")

    # 创建测试数据
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100)
    })

    # 初始化存储
    storage = DataStorage(base_path="data")

    # 测试CSV存储
    csv_path = storage.save_to_csv(test_data, "test_stock", "raw")
    loaded_csv = storage.load_from_csv("test_stock", "raw")
    print(f"\nCSV存储测试: 保存 {len(test_data)} 行, 加载 {len(loaded_csv)} 行")

    # 测试Parquet存储
    parquet_path = storage.save_to_parquet(test_data, "test_stock", "processed")
    loaded_parquet = storage.load_from_parquet("test_stock", "processed")
    print(f"Parquet存储测试: 保存 {len(test_data)} 行, 加载 {len(loaded_parquet)} 行")

    # 测试缓存
    cache = DataCache(max_size=10)
    cache.set("test_key", test_data)
    cached_data = cache.get("test_key")
    print(f"\n缓存测试: {'成功' if cached_data is not None else '失败'}")
    print(f"缓存统计: {cache.stats()}")

    # 存储统计
    print(f"\n存储统计: {storage.get_storage_stats()}")
