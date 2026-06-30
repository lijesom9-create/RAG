"""
Agent 生命周期状态机测试
"""

import pytest
from app.models.lifecycle import AgentLifecycle, AgentStatus, WaitingReason


class TestAgentLifecycle:
    """生命周期状态机测试"""

    def test_initial_state(self):
        """初始状态应为 CREATED"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        assert lifecycle.status == AgentStatus.CREATED
        assert lifecycle.retry_count == 0
        assert lifecycle.version == 1

    def test_created_to_planning(self):
        """CREATED → PLANNING 转换"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        assert lifecycle.status == AgentStatus.PLANNING
        assert lifecycle.version == 2

    def test_planning_to_executing(self):
        """PLANNING → EXECUTING 转换"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        assert lifecycle.status == AgentStatus.EXECUTING

    def test_executing_to_completed(self):
        """EXECUTING → COMPLETED 转换"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        lifecycle.transition_to(AgentStatus.COMPLETED)
        assert lifecycle.status == AgentStatus.COMPLETED

    def test_full_happy_path(self):
        """完整 happy path: CREATED → ... → ARCHIVED"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        lifecycle.transition_to(AgentStatus.COMPLETED)
        lifecycle.transition_to(AgentStatus.EVALUATED)
        lifecycle.transition_to(AgentStatus.LEARNED)
        lifecycle.transition_to(AgentStatus.ARCHIVED)
        assert lifecycle.status == AgentStatus.ARCHIVED
        assert lifecycle.is_terminal()

    def test_invalid_transition_raises(self):
        """非法状态转换应抛出 ValueError"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        with pytest.raises(ValueError, match="非法状态转换"):
            lifecycle.transition_to(AgentStatus.COMPLETED)

    def test_fail_from_planning(self):
        """从 PLANNING 进入 FAILED"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.fail("测试错误")
        assert lifecycle.status == AgentStatus.FAILED
        assert lifecycle.error_message == "测试错误"

    def test_fail_from_executing(self):
        """从 EXECUTING 进入 FAILED"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        lifecycle.fail("执行错误")
        assert lifecycle.status == AgentStatus.FAILED

    def test_retry_from_failed(self):
        """从 FAILED 重试回到 PLANNING"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.fail("错误")
        lifecycle.retry()
        assert lifecycle.status == AgentStatus.PLANNING
        assert lifecycle.retry_count == 1

    def test_retry_max_exceeded(self):
        """超过最大重试次数应抛出 ValueError"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.max_retries = 2
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.fail("错误1")
        lifecycle.retry()
        lifecycle.fail("错误2")
        lifecycle.retry()
        lifecycle.fail("错误3")
        with pytest.raises(ValueError, match="超过最大重试次数"):
            lifecycle.retry()

    def test_retry_only_from_failed(self):
        """只有 FAILED 状态才能重试"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        with pytest.raises(ValueError, match="只有 Failed 状态才能重试"):
            lifecycle.retry()

    def test_cancel(self):
        """用户主动取消"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.cancel()
        assert lifecycle.status == AgentStatus.CANCELLED
        assert lifecycle.is_terminal()

    def test_waiting_requires_reason(self):
        """进入 WAITING 状态必须指定 waiting_reason"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        with pytest.raises(ValueError, match="必须指定 waiting_reason"):
            lifecycle.transition_to(AgentStatus.WAITING)

    def test_waiting_with_reason(self):
        """进入 WAITING 状态并指定 waiting_reason"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)
        lifecycle.transition_to(
            AgentStatus.WAITING,
            waiting_reason=WaitingReason.EXTERNAL_TOOL,
        )
        assert lifecycle.status == AgentStatus.WAITING
        assert lifecycle.waiting_reason == WaitingReason.EXTERNAL_TOOL

    def test_can_retry(self):
        """can_retry 方法"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        assert not lifecycle.can_retry()

        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.fail("错误")
        assert lifecycle.can_retry()

    def test_serialization(self):
        """序列化/反序列化"""
        lifecycle = AgentLifecycle(agent_id="test_agent")
        lifecycle.transition_to(AgentStatus.PLANNING)
        lifecycle.transition_to(AgentStatus.EXECUTING)

        data = lifecycle.to_dict()
        restored = AgentLifecycle.from_dict(data)

        assert restored.agent_id == "test_agent"
        assert restored.status == AgentStatus.EXECUTING
        assert restored.version == lifecycle.version
