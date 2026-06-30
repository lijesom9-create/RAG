"""
Agent 状态定义

定义 LangGraph Agent 的状态结构。
"""

from typing import List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    Agent 状态

    继承 MessagesState，添加自定义字段。
    """
    # 工具调用记录
    tools_used: List[str] = []
    tool_results: Dict[str, Any] = {}

    # 任务信息
    task_type: str = ""  # 问答、总结、生成
    task_context: Dict[str, Any] = {}

    # RAG 检索结果
    retrieved_docs: List[Dict] = []
    citations: List[Dict] = []

    # 反思
    reflection: Optional[Dict] = None
    should_retry: bool = False

    # 执行信息
    step_count: int = 0
    max_steps: int = 8
