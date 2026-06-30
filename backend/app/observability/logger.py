"""
Structured Logger - 结构化日志器

提供结构化日志，支持：
- JSON 格式日志
- 上下文关联
- 日志级别
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger


class StructuredLogger:
    """
    结构化日志器

    提供结构化日志，便于分析和查询。
    """

    def __init__(self, context: Dict = None):
        self.context = context or {}
        self.logs = []

    def set_context(self, key: str, value: Any):
        """设置上下文"""
        self.context[key] = value

    def clear_context(self):
        """清除上下文"""
        self.context.clear()

    def log(
        self,
        level: str,
        message: str,
        data: Dict = None,
    ):
        """记录日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "context": self.context.copy(),
            "data": data or {},
        }

        self.logs.append(log_entry)

        # 限制日志数量
        if len(self.logs) > 10000:
            self.logs = self.logs[-10000:]

        # 调用 loguru
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message, **(data or {}))

    def info(self, message: str, data: Dict = None):
        """记录信息日志"""
        self.log("INFO", message, data)

    def warning(self, message: str, data: Dict = None):
        """记录警告日志"""
        self.log("WARNING", message, data)

    def error(self, message: str, data: Dict = None):
        """记录错误日志"""
        self.log("ERROR", message, data)

    def debug(self, message: str, data: Dict = None):
        """记录调试日志"""
        self.log("DEBUG", message, data)

    def get_logs(
        self,
        level: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取日志"""
        logs = self.logs
        if level:
            logs = [l for l in logs if l["level"] == level]
        return logs[-limit:]

    def get_logs_by_context(
        self,
        key: str,
        value: Any,
        limit: int = 100,
    ) -> List[Dict]:
        """按上下文获取日志"""
        logs = [
            l for l in logs
            if l["context"].get(key) == value
        ]
        return logs[-limit:]

    def clear(self):
        """清除日志"""
        self.logs.clear()

    def export_json(self) -> str:
        """导出为 JSON"""
        return json.dumps(self.logs, ensure_ascii=False, indent=2)


# 全局日志实例
_structured_logger: Optional[StructuredLogger] = None


def get_structured_logger() -> StructuredLogger:
    """获取全局结构化日志器"""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger
