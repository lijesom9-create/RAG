"""
核心数据模型测试
"""

import pytest
from app.models.step import Step
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.evaluation import EvaluationRecord
from app.models.learning_insight import LearningInsight
from app.models.optimization_change import OptimizationChange
from app.models.session import Session, Conversation
from app.models.lifecycle import AgentStatus


class TestStep:
    """Step 模型测试"""

    def test_create_step(self):
        """创建 Step"""
        step = Step(name="讲解概念", description="讲解递归概念")
        assert step.name == "讲解概念"
        assert step.status == AgentStatus.CREATED
        assert step.depends_on == []
        assert step.agents == []

    def test_dependency(self):
        """依赖关系"""
        step = Step(name="练习")
        step.add_dependency("step_1")
        step.add_dependency("step_2")
        assert step.depends_on == ["step_1", "step_2"]

        step.remove_dependency("step_1")
        assert step.depends_on == ["step_2"]

    def test_is_ready(self):
        """检查是否可以执行"""
        step = Step(name="练习", depends_on=["step_1", "step_2"])
        assert not step.is_ready(["step_1"])
        assert step.is_ready(["step_1", "step_2"])
        assert step.is_ready(["step_1", "step_2", "step_3"])

    def test_multi_agent(self):
        """多 Agent 协作"""
        step = Step(name="复杂任务")
        step.add_agent("agent_1")
        step.add_agent("agent_2")
        assert len(step.agents) == 2

    def test_serialization(self):
        """序列化/反序列化"""
        step = Step(name="测试步骤", depends_on=["dep_1"], agents=["agent_1"])
        data = step.to_dict()
        restored = Step.from_dict(data)
        assert restored.name == "测试步骤"
        assert restored.depends_on == ["dep_1"]
        assert restored.agents == ["agent_1"]


class TestWorkflow:
    """Workflow 模型测试"""

    def test_create_workflow(self):
        """创建 Workflow"""
        wf = Workflow(name="教学流程")
        assert wf.name == "教学流程"
        assert wf.steps == []

    def test_add_step(self):
        """添加步骤"""
        wf = Workflow(name="教学流程")
        step1 = Step(name="讲解")
        step2 = Step(name="练习", depends_on=[step1.id])
        wf.add_step(step1)
        wf.add_step(step2)
        assert len(wf.steps) == 2
        assert wf.steps[0].workflow_id == wf.id

    def test_get_ready_steps(self):
        """获取可以执行的步骤"""
        wf = Workflow(name="教学流程")
        step1 = Step(name="讲解")
        step2 = Step(name="练习", depends_on=[step1.id])
        wf.add_step(step1)
        wf.add_step(step2)

        # step1 没有依赖，应该 ready
        ready = wf.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == step1.id

        # step1 完成后，step2 应该 ready
        step1.status = AgentStatus.COMPLETED
        ready = wf.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == step2.id

    def test_execution_order(self):
        """拓扑排序"""
        wf = Workflow(name="教学流程")
        step1 = Step(name="讲解")
        step2 = Step(name="练习", depends_on=[step1.id])
        step3 = Step(name="复习")
        wf.add_step(step1)
        wf.add_step(step2)
        wf.add_step(step3)

        layers = wf.get_execution_order()
        # 第一层：step1, step3（无依赖）
        # 第二层：step2（依赖 step1）
        assert len(layers) == 2
        layer1_ids = {s.id for s in layers[0]}
        assert step1.id in layer1_ids
        assert step3.id in layer1_ids
        assert layers[1][0].id == step2.id

    def test_serialization(self):
        """序列化/反序列化"""
        wf = Workflow(name="教学流程")
        wf.add_step(Step(name="讲解"))
        wf.add_step(Step(name="练习"))
        data = wf.to_dict()
        restored = Workflow.from_dict(data)
        assert restored.name == "教学流程"
        assert len(restored.steps) == 2


class TestTask:
    """Task 模型测试"""

    def test_create_task(self):
        """创建 Task"""
        task = Task(user_id="user_1", name="学习递归")
        assert task.user_id == "user_1"
        assert task.workflows == []

    def test_add_workflow(self):
        """添加工作流"""
        task = Task(user_id="user_1", name="学习递归")
        wf = Workflow(name="教学流程")
        task.add_workflow(wf)
        assert len(task.workflows) == 1
        assert task.workflows[0].task_id == task.id

    def test_serialization(self):
        """序列化/反序列化"""
        task = Task(user_id="user_1", name="学习递归")
        task.add_workflow(Workflow(name="教学流程"))
        data = task.to_dict()
        restored = Task.from_dict(data)
        assert restored.user_id == "user_1"
        assert len(restored.workflows) == 1


class TestEvaluationRecord:
    """EvaluationRecord 模型测试"""

    def test_create_record(self):
        """创建评估记录"""
        record = EvaluationRecord(
            result_id="result_1",
            user_id="user_1",
            skill_name="practice_session",
            score=0.85,
            metrics={"accuracy": 0.9, "speed": 0.8},
        )
        assert record.score == 0.85
        assert record.metrics["accuracy"] == 0.9

    def test_serialization(self):
        """序列化/反序列化"""
        record = EvaluationRecord(
            result_id="result_1",
            user_id="user_1",
            score=0.85,
        )
        data = record.to_dict()
        restored = EvaluationRecord.from_dict(data)
        assert restored.score == 0.85
        assert restored.result_id == "result_1"


class TestLearningInsight:
    """LearningInsight 模型测试"""

    def test_create_insight(self):
        """创建学习洞察"""
        insight = LearningInsight(
            eval_ids=["eval_1", "eval_2"],
            category="difficulty",
            finding="学生在递归题目上正确率较低",
            suggestion="建议降低递归题目难度",
            confidence=0.8,
        )
        assert insight.category == "difficulty"
        assert len(insight.eval_ids) == 2

    def test_serialization(self):
        """序列化/反序列化"""
        insight = LearningInsight(
            category="style",
            finding="学生偏好类比讲解",
            suggestion="多用类比方式",
        )
        data = insight.to_dict()
        restored = LearningInsight.from_dict(data)
        assert restored.category == "style"


class TestOptimizationChange:
    """OptimizationChange 模型测试"""

    def test_create_change(self):
        """创建优化变更"""
        change = OptimizationChange(
            insight_id="insight_1",
            target_type="prompt",
            target_id="system_prompt_v1",
            old_version=1,
            new_version=2,
            old_value="旧提示",
            new_value="新提示",
            reason="根据学习洞察优化",
        )
        assert not change.applied
        assert change.old_version == 1
        assert change.new_version == 2

    def test_apply(self):
        """标记为已应用"""
        change = OptimizationChange(
            insight_id="insight_1",
            target_type="strategy",
            target_id="difficulty_strategy",
        )
        assert not change.applied
        change.apply()
        assert change.applied

    def test_serialization(self):
        """序列化/反序列化"""
        change = OptimizationChange(
            insight_id="insight_1",
            target_type="prompt",
            target_id="prompt_v1",
            old_version=1,
            new_version=2,
        )
        data = change.to_dict()
        restored = OptimizationChange.from_dict(data)
        assert restored.target_type == "prompt"
        assert restored.old_version == 1


class TestSession:
    """Session / Conversation 模型测试"""

    def test_conversation(self):
        """创建对话"""
        conv = Conversation(
            session_id="session_1",
            user_input="什么是递归？",
            agent_response="递归是...",
            skill_used="concept_lesson",
        )
        assert conv.user_input == "什么是递归？"

    def test_session(self):
        """创建会话"""
        session = Session(user_id="user_1")
        conv1 = Conversation(user_input="问题1", agent_response="回答1")
        conv2 = Conversation(user_input="问题2", agent_response="回答2")
        session.add_conversation(conv1)
        session.add_conversation(conv2)
        assert len(session.conversations) == 2
        assert session.conversations[0].session_id == session.id

    def test_get_recent(self):
        """获取最近对话"""
        session = Session(user_id="user_1")
        for i in range(10):
            session.add_conversation(
                Conversation(user_input=f"问题{i}", agent_response=f"回答{i}")
            )
        recent = session.get_recent_conversations(3)
        assert len(recent) == 3
        assert recent[0].user_input == "问题7"

    def test_serialization(self):
        """序列化/反序列化"""
        session = Session(user_id="user_1", summary="学习了递归")
        session.add_conversation(Conversation(user_input="问题", agent_response="回答"))
        data = session.to_dict()
        restored = Session.from_dict(data)
        assert restored.user_id == "user_1"
        assert restored.summary == "学习了递归"
        assert len(restored.conversations) == 1
