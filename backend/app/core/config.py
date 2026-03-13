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

    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/dlqi"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 数据源配置
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 模型配置
    MODEL_DIR: str = os.getenv("MODEL_DIR", "../data/models")
    DATA_DIR: str = os.getenv("DATA_DIR", "../data")

    # 回测配置
    DEFAULT_INITIAL_CAPITAL: float = 1000000.0
    DEFAULT_COMMISSION_RATE: float = 0.0003
    DEFAULT_SLIPPAGE: float = 0.001

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
