"""
存储服务模块

提供文件系统存储功能。
"""

from .file_storage import FileStorage, get_file_storage

__all__ = ["FileStorage", "get_file_storage"]
