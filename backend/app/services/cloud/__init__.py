"""
云端模型服务模块

支持通过 Google Drive 与 Colab 通信，无需付费隧道服务
"""

from app.services.cloud.client import ModelServiceClient
from app.services.cloud.tasks import TaskQueue
from app.services.cloud.drive import GoogleDriveClient, ColabModelRegistry

__all__ = [
    "ModelServiceClient",
    "TaskQueue",
    "GoogleDriveClient",
    "ColabModelRegistry"
]
