"""
Metrics - 指标收集器

收集 Agent 执行指标，支持：
- 计数器
- 直方图
- 仪表盘
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器（递增）
    GAUGE = "gauge"          # 仪表盘（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布）


@dataclass
class Metric:
    """指标"""
    name: str
    type: MetricType
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


class Metrics:
    """
    指标收集器

    收集 Agent 执行指标。
    """

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.history: List[Metric] = []

    def increment(self, name: str, value: float = 1.0, labels: Dict = None):
        """增加计数器"""
        key = self._get_key(name, labels)
        if key not in self.metrics:
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.COUNTER,
                labels=labels or {},
            )

        self.metrics[key].value += value
        self.metrics[key].timestamp = datetime.now().isoformat()

        # 记录历史
        self.history.append(Metric(
            name=name,
            type=MetricType.COUNTER,
            value=value,
            labels=labels or {},
        ))

    def set_gauge(self, name: str, value: float, labels: Dict = None):
        """设置仪表盘"""
        key = self._get_key(name, labels)
        self.metrics[key] = Metric(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
            timestamp=datetime.now().isoformat(),
        )

    def observe(self, name: str, value: float, labels: Dict = None):
        """记录直方图观测值"""
        key = self._get_key(name, labels)
        if key not in self.metrics:
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                labels=labels or {},
            )

        # 简化：只记录最新值
        self.metrics[key].value = value
        self.metrics[key].timestamp = datetime.now().isoformat()

        # 记录历史
        self.history.append(Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            labels=labels or {},
        ))

    def get_metric(self, name: str, labels: Dict = None) -> Optional[Metric]:
        """获取指标"""
        key = self._get_key(name, labels)
        return self.metrics.get(key)

    def get_all_metrics(self) -> List[Dict]:
        """获取所有指标"""
        return [m.to_dict() for m in self.metrics.values()]

    def get_history(self, name: str = None, limit: int = 100) -> List[Dict]:
        """获取历史记录"""
        history = self.history
        if name:
            history = [m for m in history if m.name == name]
        return [m.to_dict() for m in history[-limit:]]

    def _get_key(self, name: str, labels: Dict = None) -> str:
        """获取指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def reset(self):
        """重置所有指标"""
        self.metrics.clear()
        self.history.clear()


# 预定义指标
AGENT_EXECUTION_TOTAL = "agent_execution_total"
AGENT_EXECUTION_DURATION = "agent_execution_duration_ms"
AGENT_EXECUTION_ERRORS = "agent_execution_errors"
TOOL_CALL_TOTAL = "tool_call_total"
TOOL_CALL_DURATION = "tool_call_duration_ms"
TOOL_CALL_ERRORS = "tool_call_errors"
LLM_CALL_TOTAL = "llm_call_total"
LLM_CALL_DURATION = "llm_call_duration_ms"
LLM_CALL_TOKENS = "llm_call_tokens"


def create_default_metrics() -> Metrics:
    """创建默认指标"""
    metrics = Metrics()

    # 初始化计数器
    metrics.set_gauge(AGENT_EXECUTION_TOTAL, 0)
    metrics.set_gauge(AGENT_EXECUTION_ERRORS, 0)
    metrics.set_gauge(TOOL_CALL_TOTAL, 0)
    metrics.set_gauge(TOOL_CALL_ERRORS, 0)
    metrics.set_gauge(LLM_CALL_TOTAL, 0)

    return metrics


# 全局指标实例
_metrics: Optional[Metrics] = None


def get_metrics() -> Metrics:
    """获取全局指标"""
    global _metrics
    if _metrics is None:
        _metrics = create_default_metrics()
    return _metrics
