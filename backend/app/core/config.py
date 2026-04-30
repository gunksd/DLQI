"""
应用配置
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用设置"""

    # 基本配置
    APP_NAME: str = "DLQI"
    DEBUG: bool = True

    # Supabase PostgreSQL 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # 模型配置
    MODEL_DIR: str = os.getenv("MODEL_DIR", "../data/models")
    DATA_DIR: str = os.getenv("DATA_DIR", "../data")

    # A 股股票池
    STOCK_POOL: List[str] = ["600519", "601318", "600036", "300750", "002594"]
    STOCK_NAMES: dict = {
        "600519": "贵州茅台", "601318": "中国平安", "600036": "招商银行",
        "300750": "宁德时代", "002594": "比亚迪",
    }

    # 回测配置（A 股费率）
    DEFAULT_INITIAL_CAPITAL: float = 1000000.0
    DEFAULT_COMMISSION_RATE: float = 0.00025  # 万2.5
    DEFAULT_SLIPPAGE: float = 0.001
    STAMP_TAX_RATE: float = 0.0005  # 印花税 0.05%（卖出）

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
