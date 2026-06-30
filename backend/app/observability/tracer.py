"""
Tracer - 链路追踪器

追踪 Agent 执行过程，支持：
- 链路追踪
- 性能分析
- 错误定位
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class Span:
    """追踪跨度"""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    status: str = "ok"  # ok, error, timeout
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }

    def add_event(self, name: str, attributes: Dict = None):
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {},
        })

    def finish(self, status: str = "ok"):
        """完成跨度"""
        self.end_time = datetime.now().isoformat()
        self.status = status

        # 计算耗时
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_ms = (end - start).total_seconds() * 1000


class Tracer:
    """
    链路追踪器

    追踪 Agent 执行过程。
    """

    def __init__(self):
        self.traces: Dict[str, List[Span]] = {}
        self.current_trace_id: Optional[str] = None
        self.current_span_id: Optional[str] = None

    def start_trace(self, trace_id: str, name: str) -> Span:
        """开始追踪"""
        span = Span(
            trace_id=trace_id,
            span_id=f"{trace_id}_root",
            parent_id=None,
            name=name,
            start_time=datetime.now().isoformat(),
        )

        self.traces[trace_id] = [span]
        self.current_trace_id = trace_id
        self.current_span_id = span.span_id

        logger.debug(f"开始追踪: {trace_id}")
        return span

    def start_span(
        self,
        name: str,
        attributes: Dict = None,
    ) -> Span:
        """开始跨度"""
        if not self.current_trace_id:
            logger.warning("没有活跃的追踪")
            return None

        span_id = f"{self.current_trace_id}_{len(self.traces[self.current_trace_id])}"
        span = Span(
            trace_id=self.current_trace_id,
            span_id=span_id,
            parent_id=self.current_span_id,
            name=name,
            start_time=datetime.now().isoformat(),
            attributes=attributes or {},
        )

        self.traces[self.current_trace_id].append(span)
        self.current_span_id = span_id

        logger.debug(f"开始跨度: {name}")
        return span

    def finish_span(self, span: Span, status: str = "ok"):
        """完成跨度"""
        span.finish(status)
        logger.debug(f"完成跨度: {span.name} ({span.duration_ms:.1f}ms)")

    def finish_trace(self, trace_id: str):
        """完成追踪"""
        if trace_id in self.traces:
            for span in self.traces[trace_id]:
                if not span.end_time:
                    span.finish()

            logger.debug(f"完成追踪: {trace_id}")

    def get_trace(self, trace_id: str) -> List[Dict]:
        """获取追踪"""
        spans = self.traces.get(trace_id, [])
        return [s.to_dict() for s in spans]

    def get_all_traces(self) -> Dict[str, List[Dict]]:
        """获取所有追踪"""
        return {
            trace_id: [s.to_dict() for s in spans]
            for trace_id, spans in self.traces.items()
        }

    def get_summary(self, trace_id: str) -> Dict:
        """获取追踪摘要"""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return {}

        total_duration = sum(s.duration_ms or 0 for s in spans)
        error_count = sum(1 for s in spans if s.status == "error")

        return {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "total_duration_ms": total_duration,
            "error_count": error_count,
            "root_span": spans[0].name if spans else None,
        }

    def print_trace(self, trace_id: str):
        """打印追踪（调试用）"""
        spans = self.traces.get(trace_id, [])
        if not spans:
            print(f"追踪不存在: {trace_id}")
            return

        print(f"\n{'='*60}")
        print(f"追踪: {trace_id}")
        print(f"{'='*60}")

        for span in spans:
            indent = "  " * (span.name.count(".") + 1)
            duration = f"{span.duration_ms:.1f}ms" if span.duration_ms else "进行中"
            status = "✓" if span.status == "ok" else "✗"

            print(f"{indent}{status} {span.name} ({duration})")

            if span.attributes:
                for key, value in span.attributes.items():
                    print(f"{indent}    {key}: {value}")

        print(f"{'='*60}\n")


# 全局追踪器实例
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """获取全局追踪器"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
