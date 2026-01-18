"""
云端模型服务客户端
用于与云端GPU服务器通信，提交训练任务和获取预测结果
"""

import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainConfig(BaseModel):
    """训练配置"""
    model_type: str  # lstm, transformer, lightgbm, xgboost, ensemble
    symbols: List[str]
    start_date: str
    end_date: str
    features: Optional[List[str]] = None

    # 模型参数
    params: Optional[Dict[str, Any]] = None

    # 训练参数
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    validation_split: float = 0.2
    early_stopping: bool = True
    patience: int = 10

    # GPU设置
    use_gpu: bool = True
    gpu_id: int = 0


class PredictConfig(BaseModel):
    """预测配置"""
    model_id: str
    symbols: List[str]
    start_date: str
    end_date: Optional[str] = None
    horizon: int = 5  # 预测天数


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class ModelServiceClient:
    """
    云端模型服务客户端

    负责与远程GPU服务器通信，包括：
    - 提交模型训练任务
    - 查询任务状态
    - 获取预测结果
    - 管理模型版本
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化客户端

        Args:
            base_url: 云端服务地址
            api_key: API密钥
            timeout: 请求超时时间
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ==================== 健康检查 ====================

    async def health_check(self) -> Dict[str, Any]:
        """
        检查云端服务状态

        Returns:
            服务状态信息
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_gpu_status(self) -> Dict[str, Any]:
        """
        获取GPU状态

        Returns:
            GPU使用情况
        """
        try:
            client = await self._get_client()
            response = await client.get("/gpu/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Get GPU status failed: {e}")
            return {"available": False, "error": str(e)}

    # ==================== 训练任务 ====================

    async def submit_training(self, config: TrainConfig) -> TaskResult:
        """
        提交训练任务

        Args:
            config: 训练配置

        Returns:
            任务信息
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/tasks/train",
                json=config.model_dump()
            )
            response.raise_for_status()
            data = response.json()
            return TaskResult(**data)
        except httpx.HTTPStatusError as e:
            logger.error(f"Submit training failed: {e}")
            raise RuntimeError(f"提交训练任务失败: {e.response.text}")
        except Exception as e:
            logger.error(f"Submit training failed: {e}")
            raise RuntimeError(f"提交训练任务失败: {e}")

    async def get_task_status(self, task_id: str) -> TaskResult:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/tasks/{task_id}")
            response.raise_for_status()
            data = response.json()
            return TaskResult(**data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"任务不存在: {task_id}")
            raise RuntimeError(f"获取任务状态失败: {e.response.text}")
        except Exception as e:
            logger.error(f"Get task status failed: {e}")
            raise RuntimeError(f"获取任务状态失败: {e}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/tasks/{task_id}/cancel")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Cancel task failed: {e}")
            return False

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[TaskResult]:
        """
        列出任务

        Args:
            status: 过滤状态
            limit: 返回数量
            offset: 偏移量

        Returns:
            任务列表
        """
        try:
            client = await self._get_client()
            params = {"limit": limit, "offset": offset}
            if status:
                params["status"] = status.value

            response = await client.get("/tasks", params=params)
            response.raise_for_status()
            data = response.json()
            return [TaskResult(**item) for item in data.get("tasks", [])]
        except Exception as e:
            logger.error(f"List tasks failed: {e}")
            return []

    async def wait_for_task(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        timeout: float = 3600.0
    ) -> TaskResult:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔(秒)
            timeout: 超时时间(秒)

        Returns:
            最终任务状态
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await self.get_task_status(task_id)

            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return result

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"等待任务超时: {task_id}")

            await asyncio.sleep(poll_interval)

    # ==================== 预测服务 ====================

    async def predict(self, config: PredictConfig) -> Dict[str, Any]:
        """
        执行预测

        Args:
            config: 预测配置

        Returns:
            预测结果
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/predict",
                json=config.model_dump(),
                timeout=60.0  # 预测可能需要更长时间
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Predict failed: {e}")
            raise RuntimeError(f"预测失败: {e.response.text}")
        except Exception as e:
            logger.error(f"Predict failed: {e}")
            raise RuntimeError(f"预测失败: {e}")

    async def batch_predict(
        self,
        model_id: str,
        symbols: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量预测

        Args:
            model_id: 模型ID
            symbols: 股票列表
            **kwargs: 其他参数

        Returns:
            批量预测结果
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/predict/batch",
                json={
                    "model_id": model_id,
                    "symbols": symbols,
                    **kwargs
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Batch predict failed: {e}")
            raise RuntimeError(f"批量预测失败: {e}")

    # ==================== 模型管理 ====================

    async def list_models(
        self,
        model_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        列出可用模型

        Args:
            model_type: 模型类型过滤
            limit: 返回数量

        Returns:
            模型列表
        """
        try:
            client = await self._get_client()
            params = {"limit": limit}
            if model_type:
                params["type"] = model_type

            response = await client.get("/models", params=params)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"List models failed: {e}")
            return []

    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """
        获取模型详情

        Args:
            model_id: 模型ID

        Returns:
            模型信息
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/models/{model_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"模型不存在: {model_id}")
            raise RuntimeError(f"获取模型信息失败: {e.response.text}")
        except Exception as e:
            logger.error(f"Get model failed: {e}")
            raise RuntimeError(f"获取模型信息失败: {e}")

    async def delete_model(self, model_id: str) -> bool:
        """
        删除模型

        Args:
            model_id: 模型ID

        Returns:
            是否成功删除
        """
        try:
            client = await self._get_client()
            response = await client.delete(f"/models/{model_id}")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Delete model failed: {e}")
            return False

    async def download_model(self, model_id: str, save_path: str) -> bool:
        """
        下载模型文件

        Args:
            model_id: 模型ID
            save_path: 保存路径

        Returns:
            是否成功下载
        """
        try:
            client = await self._get_client()
            async with client.stream("GET", f"/models/{model_id}/download") as response:
                response.raise_for_status()
                with open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Download model failed: {e}")
            return False

    async def upload_model(
        self,
        model_path: str,
        model_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        上传模型文件

        Args:
            model_path: 模型文件路径
            model_type: 模型类型
            metadata: 模型元数据

        Returns:
            上传结果
        """
        try:
            with open(model_path, "rb") as f:
                files = {"file": f}
                data = {"model_type": model_type}
                if metadata:
                    data["metadata"] = json.dumps(metadata)

                client = await self._get_client()
                response = await client.post(
                    "/models/upload",
                    files=files,
                    data=data,
                    timeout=300.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Upload model failed: {e}")
            raise RuntimeError(f"上传模型失败: {e}")

    # ==================== 模型评估 ====================

    async def evaluate_model(
        self,
        model_id: str,
        test_symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        评估模型

        Args:
            model_id: 模型ID
            test_symbols: 测试股票
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            评估结果
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"/models/{model_id}/evaluate",
                json={
                    "symbols": test_symbols,
                    "start_date": start_date,
                    "end_date": end_date
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Evaluate model failed: {e}")
            raise RuntimeError(f"模型评估失败: {e}")

    # ==================== 超参数优化 ====================

    async def submit_hyperparameter_tuning(
        self,
        model_type: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        param_space: Dict[str, Any],
        n_trials: int = 50,
        optimization_metric: str = "sharpe_ratio"
    ) -> TaskResult:
        """
        提交超参数优化任务

        Args:
            model_type: 模型类型
            symbols: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            param_space: 参数搜索空间
            n_trials: 尝试次数
            optimization_metric: 优化指标

        Returns:
            任务信息
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/tasks/tune",
                json={
                    "model_type": model_type,
                    "symbols": symbols,
                    "start_date": start_date,
                    "end_date": end_date,
                    "param_space": param_space,
                    "n_trials": n_trials,
                    "optimization_metric": optimization_metric
                }
            )
            response.raise_for_status()
            data = response.json()
            return TaskResult(**data)
        except Exception as e:
            logger.error(f"Submit tuning failed: {e}")
            raise RuntimeError(f"提交超参数优化任务失败: {e}")


# 便捷函数
async def create_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> ModelServiceClient:
    """
    创建模型服务客户端

    Args:
        base_url: 服务地址，默认从环境变量读取
        api_key: API密钥，默认从环境变量读取

    Returns:
        客户端实例
    """
    import os

    url = base_url or os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")
    key = api_key or os.getenv("MODEL_SERVICE_API_KEY")

    return ModelServiceClient(base_url=url, api_key=key)
