"""
异步任务队列
支持本地任务和 Colab 远程任务
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    task_type: str
    status: TaskStatus
    progress: float = 0.0
    message: Optional[str] = None
    params: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskQueue:
    """
    任务队列管理器

    支持:
    - 本地任务执行
    - 远程 Colab 任务提交
    - 任务状态跟踪
    - 结果存储
    """

    def __init__(self, storage_path: str = "./task_storage"):
        """
        初始化任务队列

        Args:
            storage_path: 任务存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, TaskInfo] = {}
        self.handlers: Dict[str, Callable] = {}
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()

        # 加载持久化的任务
        self._load_tasks()

    def _load_tasks(self):
        """从存储加载任务"""
        task_file = self.storage_path / "tasks.json"
        if task_file.exists():
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = TaskInfo(**task_data)
                        self.tasks[task.task_id] = task
                logger.info(f"Loaded {len(self.tasks)} tasks from storage")
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")

    def _save_tasks(self):
        """保存任务到存储"""
        task_file = self.storage_path / "tasks.json"
        try:
            data = [task.model_dump(mode='json') for task in self.tasks.values()]
            with open(task_file, "w") as f:
                json.dump(data, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler: 异步处理函数
        """
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def submit(
        self,
        task_type: str,
        params: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        提交任务

        Args:
            task_type: 任务类型
            params: 任务参数
            priority: 优先级

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        task = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            params=params,
            created_at=now,
            updated_at=now
        )

        self.tasks[task_id] = task
        self._save_tasks()

        await self._queue.put((priority, task_id))
        logger.info(f"Task submitted: {task_id} ({task_type})")

        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskInfo]:
        """列出任务"""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now()
            self._save_tasks()
            logger.info(f"Task cancelled: {task_id}")
            return True

        return False

    async def update_progress(
        self,
        task_id: str,
        progress: float,
        message: Optional[str] = None
    ):
        """更新任务进度"""
        task = self.tasks.get(task_id)
        if task:
            task.progress = progress
            if message:
                task.message = message
            task.updated_at = datetime.now()
            self._save_tasks()

    async def _process_task(self, task_id: str):
        """处理单个任务"""
        task = self.tasks.get(task_id)
        if not task:
            return

        if task.status == TaskStatus.CANCELLED:
            return

        handler = self.handlers.get(task.task_type)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.task_type}"
            task.updated_at = datetime.now()
            self._save_tasks()
            return

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        self._save_tasks()

        try:
            # 执行任务处理器
            result = await handler(task_id, task.params, self.update_progress)

            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = result
            task.completed_at = datetime.now()
            task.updated_at = datetime.now()
            logger.info(f"Task completed: {task_id}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now()
            logger.error(f"Task failed: {task_id} - {e}")

        self._save_tasks()

    async def start_worker(self, num_workers: int = 1):
        """启动工作线程"""
        self._running = True
        logger.info(f"Starting {num_workers} task workers")

        async def worker():
            while self._running:
                try:
                    priority, task_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                    await self._process_task(task_id)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Worker error: {e}")

        workers = [asyncio.create_task(worker()) for _ in range(num_workers)]
        await asyncio.gather(*workers)

    def stop_worker(self):
        """停止工作线程"""
        self._running = False
        logger.info("Task workers stopped")

    async def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        old_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            and task.updated_at < cutoff
        ]

        for task_id in old_tasks:
            del self.tasks[task_id]

        if old_tasks:
            self._save_tasks()
            logger.info(f"Cleaned up {len(old_tasks)} old tasks")


# 全局任务队列实例
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


# 预定义的任务处理器
async def train_model_handler(
    task_id: str,
    params: Dict[str, Any],
    update_progress: Callable
) -> Dict[str, Any]:
    """
    训练模型任务处理器 (本地)

    用于简单模型或 Colab 不可用时的降级方案
    """
    await update_progress(task_id, 0.1, "加载数据...")

    # 这里实现本地训练逻辑
    # 实际使用时应调用 app.services.models 中的训练器

    await update_progress(task_id, 0.5, "训练中...")
    await asyncio.sleep(2)  # 模拟训练

    await update_progress(task_id, 0.9, "保存模型...")

    return {
        "model_id": f"local_{task_id[:8]}",
        "message": "训练完成 (本地模式)"
    }


async def colab_train_handler(
    task_id: str,
    params: Dict[str, Any],
    update_progress: Callable
) -> Dict[str, Any]:
    """
    Colab 训练任务处理器

    将任务提交到 Colab 并轮询状态
    """
    from app.services.cloud.client import ModelServiceClient

    await update_progress(task_id, 0.1, "连接 Colab 服务...")

    # 从参数获取 Colab 服务地址
    service_url = params.get("service_url")
    if not service_url:
        raise ValueError("未配置 Colab 服务地址")

    client = ModelServiceClient(base_url=service_url)

    try:
        # 检查服务状态
        health = await client.health_check()
        if health.get("status") != "healthy":
            raise RuntimeError("Colab 服务不可用")

        await update_progress(task_id, 0.2, "提交训练任务...")

        # 提交训练任务
        from app.services.cloud.client import TrainConfig
        config = TrainConfig(**params.get("train_config", {}))
        remote_task = await client.submit_training(config)

        await update_progress(task_id, 0.3, f"任务已提交: {remote_task.task_id}")

        # 轮询任务状态
        while True:
            await asyncio.sleep(5)
            status = await client.get_task_status(remote_task.task_id)

            progress = 0.3 + status.progress * 0.6
            await update_progress(task_id, progress, status.message)

            if status.status.value == "completed":
                return status.result
            elif status.status.value == "failed":
                raise RuntimeError(f"Colab 训练失败: {status.message}")
            elif status.status.value == "cancelled":
                raise RuntimeError("任务已取消")

    finally:
        await client.close()
