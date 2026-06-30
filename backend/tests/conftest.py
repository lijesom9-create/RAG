"""
测试配置
"""

import sys
import os

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 测试环境配置：禁用 LLM 意图分类和 ReAct，避免真实 LLM 调用
os.environ.setdefault("INTENT_USE_LLM", "false")
os.environ.setdefault("USE_REACT", "false")
os.environ.setdefault("USE_LOCAL_EMBEDDING", "false")

import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """
    提供 session 级别的事件循环

    避免多个 TestClient / async fixture 之间因 event loop 被关闭而报错。
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
