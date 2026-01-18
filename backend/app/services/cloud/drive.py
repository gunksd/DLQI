"""
Google Drive 集成
用于从 Google Drive 下载 Colab 训练的模型
"""

import os
import json
import shutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging
import httpx

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Google Drive 客户端

    支持:
    - 使用服务账号或 API Key 访问公开/共享文件
    - 下载模型文件
    - 列出模型目录
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        service_account_file: Optional[str] = None,
        local_cache_dir: str = "./model_cache"
    ):
        """
        初始化客户端

        Args:
            api_key: Google API Key (用于公开文件)
            service_account_file: 服务账号 JSON 文件路径
            local_cache_dir: 本地模型缓存目录
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.service_account_file = service_account_file
        self.local_cache_dir = Path(local_cache_dir)
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

        self._client: Optional[httpx.AsyncClient] = None
        self._credentials = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def download_file(
        self,
        file_id: str,
        destination: str,
        use_cache: bool = True
    ) -> str:
        """
        下载 Google Drive 文件

        Args:
            file_id: Google Drive 文件 ID
            destination: 目标路径
            use_cache: 是否使用缓存

        Returns:
            本地文件路径
        """
        # 检查缓存
        cache_path = self.local_cache_dir / file_id
        if use_cache and cache_path.exists():
            logger.info(f"Using cached file: {cache_path}")
            shutil.copy(cache_path, destination)
            return destination

        # 下载文件
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {"alt": "media"}

        if self.api_key:
            params["key"] = self.api_key

        client = await self._get_client()

        try:
            async with client.stream("GET", url, params=params) as response:
                response.raise_for_status()

                with open(destination, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

            # 保存到缓存
            if use_cache:
                shutil.copy(destination, cache_path)

            logger.info(f"Downloaded file to: {destination}")
            return destination

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to download file: {e}")
            raise RuntimeError(f"下载文件失败: {e.response.text}")

    async def download_folder(
        self,
        folder_id: str,
        destination_dir: str
    ) -> str:
        """
        下载 Google Drive 文件夹

        Args:
            folder_id: 文件夹 ID
            destination_dir: 目标目录

        Returns:
            本地目录路径
        """
        os.makedirs(destination_dir, exist_ok=True)

        # 列出文件夹内容
        files = await self.list_files(folder_id)

        for file_info in files:
            file_path = os.path.join(destination_dir, file_info["name"])

            if file_info["mimeType"] == "application/vnd.google-apps.folder":
                # 递归下载子文件夹
                await self.download_folder(file_info["id"], file_path)
            else:
                # 下载文件
                await self.download_file(file_info["id"], file_path)

        return destination_dir

    async def list_files(
        self,
        folder_id: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出文件夹内容

        Args:
            folder_id: 文件夹 ID
            query: 查询条件

        Returns:
            文件列表
        """
        url = "https://www.googleapis.com/drive/v3/files"
        params = {
            "q": f"'{folder_id}' in parents",
            "fields": "files(id, name, mimeType, size, modifiedTime)"
        }

        if query:
            params["q"] += f" and {query}"

        if self.api_key:
            params["key"] = self.api_key

        client = await self._get_client()

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("files", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            file_id: 文件 ID

        Returns:
            文件元数据
        """
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {
            "fields": "id, name, mimeType, size, modifiedTime, parents"
        }

        if self.api_key:
            params["key"] = self.api_key

        client = await self._get_client()

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise RuntimeError(f"获取文件信息失败: {e.response.text}")


class ColabModelRegistry:
    """
    Colab 模型注册表

    管理从 Google Drive 同步的模型
    """

    def __init__(
        self,
        drive_folder_id: str,
        local_model_dir: str = "./models",
        api_key: Optional[str] = None
    ):
        """
        初始化模型注册表

        Args:
            drive_folder_id: Google Drive 模型文件夹 ID
            local_model_dir: 本地模型目录
            api_key: Google API Key
        """
        self.drive_folder_id = drive_folder_id
        self.local_model_dir = Path(local_model_dir)
        self.local_model_dir.mkdir(parents=True, exist_ok=True)

        self.drive_client = GoogleDriveClient(api_key=api_key)
        self.models: Dict[str, Dict[str, Any]] = {}

        # 加载本地模型索引
        self._load_index()

    def _load_index(self):
        """加载模型索引"""
        index_file = self.local_model_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r") as f:
                    self.models = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load model index: {e}")

    def _save_index(self):
        """保存模型索引"""
        index_file = self.local_model_dir / "index.json"
        try:
            with open(index_file, "w") as f:
                json.dump(self.models, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save model index: {e}")

    async def sync_models(self) -> List[str]:
        """
        从 Google Drive 同步模型列表

        Returns:
            新发现的模型 ID 列表
        """
        try:
            files = await self.drive_client.list_files(self.drive_folder_id)
            new_models = []

            for file_info in files:
                if file_info["mimeType"] == "application/vnd.google-apps.folder":
                    model_id = file_info["name"]

                    if model_id not in self.models:
                        self.models[model_id] = {
                            "model_id": model_id,
                            "drive_folder_id": file_info["id"],
                            "modified_time": file_info.get("modifiedTime"),
                            "synced": False,
                            "local_path": None
                        }
                        new_models.append(model_id)

            self._save_index()
            logger.info(f"Synced {len(files)} models, {len(new_models)} new")
            return new_models

        except Exception as e:
            logger.error(f"Failed to sync models: {e}")
            return []

    async def download_model(self, model_id: str, force: bool = False) -> str:
        """
        下载模型到本地

        Args:
            model_id: 模型 ID
            force: 强制重新下载

        Returns:
            本地模型路径
        """
        if model_id not in self.models:
            raise ValueError(f"模型不存在: {model_id}")

        model_info = self.models[model_id]
        local_path = self.local_model_dir / model_id

        if model_info.get("synced") and local_path.exists() and not force:
            logger.info(f"Model already downloaded: {model_id}")
            return str(local_path)

        # 下载模型文件夹
        drive_folder_id = model_info["drive_folder_id"]
        await self.drive_client.download_folder(drive_folder_id, str(local_path))

        # 更新索引
        model_info["synced"] = True
        model_info["local_path"] = str(local_path)
        model_info["downloaded_at"] = datetime.now().isoformat()
        self._save_index()

        logger.info(f"Downloaded model: {model_id}")
        return str(local_path)

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        model_info = self.models.get(model_id)
        if not model_info:
            return None

        # 读取模型元数据
        local_path = model_info.get("local_path")
        if local_path:
            metadata_file = Path(local_path) / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        return {**model_info, **metadata}
                except Exception:
                    pass

        return model_info

    def list_models(
        self,
        model_type: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出模型

        Args:
            model_type: 模型类型过滤
            symbol: 股票代码过滤

        Returns:
            模型列表
        """
        models = []
        for model_id in self.models:
            info = self.get_model_info(model_id)
            if info:
                if model_type and info.get("model_type") != model_type:
                    continue
                if symbol and info.get("symbol") != symbol:
                    continue
                models.append(info)

        return models

    def delete_model(self, model_id: str) -> bool:
        """
        删除本地模型

        Args:
            model_id: 模型 ID

        Returns:
            是否成功删除
        """
        if model_id not in self.models:
            return False

        model_info = self.models[model_id]
        local_path = model_info.get("local_path")

        if local_path and Path(local_path).exists():
            shutil.rmtree(local_path)

        del self.models[model_id]
        self._save_index()

        logger.info(f"Deleted model: {model_id}")
        return True

    async def close(self):
        """关闭客户端"""
        await self.drive_client.close()


# 便捷函数
async def create_registry(
    drive_folder_id: Optional[str] = None,
    api_key: Optional[str] = None
) -> ColabModelRegistry:
    """
    创建模型注册表

    Args:
        drive_folder_id: Google Drive 文件夹 ID
        api_key: Google API Key

    Returns:
        模型注册表实例
    """
    folder_id = drive_folder_id or os.getenv("GOOGLE_DRIVE_MODEL_FOLDER_ID")
    key = api_key or os.getenv("GOOGLE_API_KEY")

    if not folder_id:
        raise ValueError("未配置 Google Drive 模型文件夹 ID")

    registry = ColabModelRegistry(
        drive_folder_id=folder_id,
        api_key=key
    )

    # 初始同步
    await registry.sync_models()

    return registry
