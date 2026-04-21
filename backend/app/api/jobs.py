"""
任务管理 API
"""

from fastapi import APIRouter, HTTPException

from app.services.job_service import job_service

router = APIRouter()


@router.get("/")
async def list_jobs(limit: int = 20):
    """获取最近的任务列表"""
    jobs = await job_service.list_jobs(limit)
    return {"items": jobs, "total": len(jobs)}


@router.get("/{job_id}")
async def get_job(job_id: str):
    """获取任务详情"""
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消任务"""
    ok = await job_service.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail="无法取消该任务")
    return {"message": "任务已取消"}
