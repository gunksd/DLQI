"""
DLQI - 基于机器学习的量化交易策略系统
FastAPI 主应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api import data, models, strategies, backtest, risk
from app.api import jobs as jobs_api
from app.api import paper_trading
from app.core.config import settings
from app.core.database import init_db
from app.services.job_service import job_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 DLQI 量化交易系统启动中...")
    await init_db()
    print("✅ SQLite 数据库就绪")
    job_service.start()
    print("✅ 任务队列就绪")
    yield
    job_service.shutdown()
    print("👋 系统关闭")


app = FastAPI(
    title="DLQI - 量化交易策略系统",
    description="基于机器学习的量化交易策略系统API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data.router, prefix="/api/data", tags=["数据管理"])
app.include_router(models.router, prefix="/api/models", tags=["模型管理"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略管理"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测系统"])
app.include_router(risk.router, prefix="/api/risk", tags=["风险控制"])
app.include_router(jobs_api.router, prefix="/api/jobs", tags=["任务管理"])
app.include_router(paper_trading.router, prefix="/api/paper-trading", tags=["模拟交易"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "DLQI - 量化交易策略系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
