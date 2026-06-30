"""
端到端测试脚本 - 递归学科完整链路

运行方式：
    cd backend
    python tests/e2e_test.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.teaching_agent import TeachingAgent
from app.models.lifecycle import AgentStatus


@pytest.mark.asyncio
async def test_recursion_full_chain():
    """测试递归学科完整链路"""

    print("=" * 60)
    print("递归学科 - 完整链路测试")
    print("=" * 60)

    # 创建 Agent
    agent = TeachingAgent()
    await agent.initialize()

    print(f"\n[INIT] Agent 初始化完成")
    print(f"  配置版本: {agent.versioned_config.current_version}")
    print(f"  配置内容: {json.dumps(agent.versioned_config.get_current(), indent=2, ensure_ascii=False)}")

    # 模拟数据库
    mock_db = AsyncMock()
    mock_db.get_student_state.return_value = None
    mock_db.save_student_state.return_value = None
    mock_db.get_long_term_memory.return_value = None
    mock_db.save_long_term_memory.return_value = None
    mock_db.get_user_profile.return_value = None
    mock_db.save_user_profile.return_value = None
    mock_db.get_knowledge_base.return_value = None
    mock_db.save_knowledge_base.return_value = None

    # 模拟 Skill
    mock_skill = AsyncMock()
    mock_skill.name = "practice_session"
    mock_skill.triggers = ["练习", "出题"]
    mock_skill.execute.return_value = MagicMock(
        content="请实现一个递归函数，计算斐波那契数列的第 n 项。\n\n示例：\n- fibonacci(0) = 0\n- fibonacci(1) = 1\n- fibonacci(5) = 5",
        skill_name="practice_session",
        should_continue=True,
        metadata={"question_id": "q_fibonacci_1"},
    )

    # 测试场景
    test_cases = [
        {"input": "给我出一道递归题", "expected_skill": "practice_session"},
        {"input": "什么是递归？", "expected_skill": "quick_explain"},
        {"input": "答案是 B", "expected_skill": "answer_feedback"},
    ]

    async def mock_understand(*args, **kwargs):
        return mock_skill

    with patch.object(TeachingAgent, "_understand_intent", side_effect=mock_understand), \
         patch("app.agent.teaching_agent._default_db", mock_db):

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'─' * 60}")
            print(f"[TEST {i}] 用户输入: {test_case['input']}")

            result = await agent.run(
                user_id="test_user_001",
                user_input=test_case["input"],
                session_id="session_recursion_001",
            )

            # 检查响应
            print(f"\n  [RESPONSE]")
            print(f"    skill_used: {result['skill_used']}")
            print(f"    lifecycle_status: {result['lifecycle']['status']}")
            print(f"    difficulty: {result['metadata'].get('difficulty', 'N/A')}")
            print(f"    strategy_version: {result['metadata'].get('strategy_version', 'N/A')}")

            # 检查可观测日志
            obs = result.get("observability", {})
            trace = obs.get("trace", [])
            summary = obs.get("summary", "")

            print(f"\n  [OBSERVABILITY]")
            print(f"    trace_steps: {len(trace)}")
            print(f"    summary: {summary}")

            # 打印关键链路
            print(f"\n  [TRACE DETAIL]")
            for step in trace:
                stage = step["stage"]
                data = step["data"]
                if stage in ["start", "policy", "intent", "evaluation"]:
                    print(f"    {stage}: {json.dumps(data, ensure_ascii=False)[:100]}")

            # 验证
            assert result["lifecycle"]["status"] == AgentStatus.COMPLETED.value, \
                f"Expected completed, got {result['lifecycle']['status']}"
            assert len(trace) > 0, "Trace should not be empty"

            print(f"\n  [PASS] Test {i} passed!")

    print(f"\n{'=' * 60}")
    print("所有测试通过!")
    print(f"{'=' * 60}")

    # 打印最终状态
    print(f"\n[FINAL STATE]")
    print(f"  配置版本: {agent.versioned_config.current_version}")
    print(f"  变更日志: {len(agent.change_log.entries)} 条")
    print(f"  待审核变更: {len(agent.change_log.get_pending_changes())} 条")


if __name__ == "__main__":
    asyncio.run(test_recursion_full_chain())
