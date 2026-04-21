"""
异步任务队列服务 — 基于 ThreadPoolExecutor + 内存/数据库状态追踪
"""

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from loguru import logger

from app.core.database import DB_AVAILABLE

if DB_AVAILABLE:
    from app.core.database import async_session, Job


def _db_ok():
    """运行时检查数据库是否可用"""
    from app.core.database import DB_AVAILABLE as _live
    return _live


class JobService:
    """管理异步任务的执行和状态"""

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running: Dict[str, Any] = {}
        self._mem_jobs: Dict[str, dict] = {}  # 内存 fallback

    def start(self):
        logger.info(f"JobService 已启动 (max_workers={self._executor._max_workers}, db={'ON' if DB_AVAILABLE else 'OFF'})")

    def shutdown(self):
        self._executor.shutdown(wait=False)
        logger.info("JobService 已关闭")

    async def submit(self, job_type: str, func: Callable, params: dict) -> str:
        """提交任务，返回 job_id"""
        job_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow()

        if _db_ok():
            async with async_session() as session:
                job = Job(id=job_id, job_type=job_type, status="pending",
                          progress=0, current_step="排队中", params=params)
                session.add(job)
                await session.commit()
        else:
            self._mem_jobs[job_id] = {
                "id": job_id, "job_type": job_type, "status": "pending",
                "progress": 0, "current_step": "排队中", "params": params,
                "result": None, "error": None,
                "created_at": now.isoformat(), "updated_at": now.isoformat(),
            }

        loop = asyncio.get_event_loop()
        self._running[job_id] = True
        self._executor.submit(self._run_task, job_id, func, params, loop)
        return job_id

    def _run_task(self, job_id: str, func: Callable, params: dict, loop: asyncio.AbstractEventLoop):
        """在线程中执行任务"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._update_job(job_id, status="running", current_step="开始执行"), loop
            ).result(timeout=5)

            def progress_cb(pct: float, step: str):
                asyncio.run_coroutine_threadsafe(
                    self._update_job(job_id, progress=pct, current_step=step), loop
                ).result(timeout=5)

            result = func(params, progress_cb)

            asyncio.run_coroutine_threadsafe(
                self._update_job(job_id, status="completed", progress=100,
                                 current_step="完成", result=result), loop
            ).result(timeout=5)
        except Exception as e:
            logger.error(f"任务 {job_id} 失败: {e}")
            try:
                asyncio.run_coroutine_threadsafe(
                    self._update_job(job_id, status="failed", current_step="失败", error=str(e)), loop
                ).result(timeout=5)
            except Exception:
                pass
        finally:
            self._running.pop(job_id, None)

    async def _update_job(self, job_id: str, **kwargs):
        """更新任务状态"""
        if _db_ok():
            async with async_session() as session:
                from sqlalchemy import update
                kwargs["updated_at"] = datetime.utcnow()
                stmt = update(Job).where(Job.id == job_id).values(**kwargs)
                await session.execute(stmt)
                await session.commit()
        else:
            if job_id in self._mem_jobs:
                self._mem_jobs[job_id].update(kwargs)
                self._mem_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    async def get_job(self, job_id: str) -> Optional[dict]:
        """查询任务状态"""
        if _db_ok():
            async with async_session() as session:
                from sqlalchemy import select
                stmt = select(Job).where(Job.id == job_id)
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                if not job:
                    return None
                return {
                    "id": job.id, "job_type": job.job_type, "status": job.status,
                    "progress": job.progress, "current_step": job.current_step,
                    "params": job.params, "result": job.result, "error": job.error,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                }
        return self._mem_jobs.get(job_id)

    async def list_jobs(self, limit: int = 20) -> list:
        """列出最近的任务"""
        if _db_ok():
            async with async_session() as session:
                from sqlalchemy import select
                stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
                result = await session.execute(stmt)
                jobs = result.scalars().all()
                return [
                    {"id": j.id, "job_type": j.job_type, "status": j.status,
                     "progress": j.progress, "current_step": j.current_step,
                     "created_at": j.created_at.isoformat() if j.created_at else None}
                    for j in jobs
                ]
        return sorted(self._mem_jobs.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:limit]

    async def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        job = await self.get_job(job_id)
        if not job or job["status"] not in ("pending", "running"):
            return False
        await self._update_job(job_id, status="cancelled", current_step="已取消")
        self._running.pop(job_id, None)
        return True


# 全局单例
job_service = JobService()
