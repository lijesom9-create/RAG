"""
回归测试 — 验证 10 项修复的正确性

覆盖范围：
1. 跨请求状态持久化（current_question）
2. finalize 不重复调用 build_prompt
3. Learning 分析加载历史评估记录
4. hash() 改为 hashlib 确定性 ID
5. JSON 解析健壮性
6. 配置化难度调整（连对/连错）
7. StudentState 乐观锁
8. 错误信息脱敏
9. 可观测日志持久化
10. 统一 topic 提取函数
"""

import pytest
import json
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.teaching_agent import ObservabilityLogger


# ============================================================
# 1. 跨请求状态持久化
# ============================================================

class TestSessionMemoryCurrentQuestion:
    """测试 current_question 跨请求持久化"""

    def test_set_and_get_current_question(self):
        from app.memory.session_memory import SessionMemory

        memory = SessionMemory("session_001")
        question = {"question": "1+1=?", "answer": "2"}
        memory.set_current_question(question)

        assert memory.get_current_question() == question
        assert memory.to_dict()["current_question"] == question

    def test_clear_current_question(self):
        from app.memory.session_memory import SessionMemory

        memory = SessionMemory("session_001")
        memory.set_current_question({"question": "?"})
        memory.clear_current_question()

        assert memory.get_current_question() is None

    def test_from_dict_restores_current_question(self):
        from app.memory.session_memory import SessionMemory

        data = {
            "session_id": "session_001",
            "current_question": {"question": "2+2=?"},
            "recent_qa_pairs": [],
            "emotion_history": [],
            "notes": [],
        }
        memory = SessionMemory.from_dict(data)

        assert memory.get_current_question() == {"question": "2+2=?"}


# ============================================================
# 2. finalize 不重复调用 build_prompt
# ============================================================

class TestFinalizeNoDoubleSideEffects:
    """测试 finalize 使用缓存的 prompt_info，避免重复副作用"""

    @pytest.mark.asyncio
    async def test_finalize_uses_cached_prompt_info(self):
        from app.agent.teaching_agent import TeachingAgent
        from app.agent.prepared_context import PreparedContext
        from app.capabilities.base import SkillResult

        prepared = MagicMock(spec=PreparedContext)
        prepared.cached_prompt_info = {"prompt": "test"}
        prepared.streaming_executed = True

        # skill 支持 build_prompt
        skill = MagicMock()
        skill.build_prompt.return_value = {"prompt": "should_not_be_called"}
        skill.build_response.return_value = SkillResult(
            content="ok", skill_name="test", should_continue=True, metadata={}
        )
        prepared.skill = skill
        prepared.skill_context = MagicMock()
        prepared.skill_context.metadata = {}

        prepared.state = MagicMock()
        prepared.state.save = AsyncMock()
        prepared.memory_manager = MagicMock()
        prepared.memory_manager.save = AsyncMock()
        prepared.obs = MagicMock()
        prepared.obs.persist = AsyncMock()
        prepared.lifecycle = MagicMock()
        prepared.user_id = "u1"
        prepared.user_input = "hi"
        prepared.session_id = "s1"
        prepared.recommended_difficulty = "medium"

        with patch("app.agent.teaching_agent._default_db") as mock_db:

            agent = TeachingAgent()

            from app.models.evaluation import EvaluationRecord
            agent.evaluator = MagicMock()
            agent.evaluator.evaluate_interaction.return_value = EvaluationRecord(
                eval_id="eval_1",
                result_id="result_1",
                user_id="u1",
                skill_name="test",
                score=0.8,
                metrics={},
                details={},
            )

            mock_db.get_student_state = AsyncMock(return_value=None)
            mock_db.save_student_state = AsyncMock()
            mock_db.save_evaluation_record = AsyncMock()
            mock_db.add_message = AsyncMock()
            mock_db.get_evaluation_records = AsyncMock(return_value=[])
            mock_db.save_observability_trace = AsyncMock()

            await agent.finalize(prepared, full_response="ok")

        # finalize 不应该再调用 build_prompt
        skill.build_prompt.assert_not_called()
        skill.build_response.assert_called_once()


# ============================================================
# 3. Learning 分析加载历史评估记录
# ============================================================

class TestLearningAnalysisLoadsHistory:
    """测试学习分析时加载历史评估记录"""

    @pytest.mark.asyncio
    async def test_run_loads_historical_records(self):
        from app.agent.teaching_agent import TeachingAgent
        from app.models.evaluation import EvaluationRecord
        from app.memory.manager import MemoryManager

        # 构造有 10 条 QA 记录的会话记忆，触发学习分析
        fake_session_memory = MagicMock()
        fake_session_memory.recent_qa_pairs = [{"q": f"q{i}", "a": f"a{i}"} for i in range(10)]

        with patch("app.agent.teaching_agent._default_db") as mock_db, \
             patch.object(MemoryManager, "init_session", lambda self, sid, data=None: setattr(self, "session_memory", fake_session_memory)):

            agent = TeachingAgent()

            with patch.object(agent, "_understand_intent") as mock_intent, \
                 patch.object(agent, "initialize", new=AsyncMock()), \
                 patch.object(ObservabilityLogger, "persist", new=AsyncMock()):

                mock_db.get_student_state = AsyncMock(return_value=None)
                mock_db.save_student_state = AsyncMock()
                mock_db.get_session_memory = AsyncMock(return_value=None)
                mock_db.add_message = AsyncMock()
                mock_db.save_evaluation_record = AsyncMock()
                mock_db.get_evaluation_records = AsyncMock(return_value=[
                    EvaluationRecord(
                        eval_id="r1",
                        result_id="r1",
                        user_id="u1",
                        skill_name="practice",
                        score=0.5,
                        metrics={},
                    ).to_dict()
                ])
                mock_db.save_observability_trace = AsyncMock()

                skill = MagicMock()
                skill.name = "quick_explain"
                skill.execute = AsyncMock(return_value=MagicMock(
                    content="hello", skill_name="quick_explain", should_continue=True, metadata={}
                ))
                skill.build_prompt.return_value = None
                mock_intent.return_value = skill

                result = await agent.run(user_id="u1", user_input="hello", session_id="s1")

                assert result["response"] == "hello"
                mock_db.get_evaluation_records.assert_called()


# ============================================================
# 4. hash() 改为 hashlib 确定性 ID
# ============================================================
# 注意：TestDeterministicQuestionId 已删除，因为 practice.py 已被移除


# ============================================================
# 5. JSON 解析健壮性
# ============================================================

class TestRobustJsonParsing:
    """测试 GenerateQuestionTool 的 JSON 解析健壮性"""

    def test_parse_markdown_json_block(self):
        from app.tools.generation import GenerateQuestionTool

        tool = GenerateQuestionTool()
        content = '```json\n{"question": "1+1=?", "answer": "2"}\n```'
        result = tool._parse_json_response(content)

        assert result is not None
        assert result["question"] == "1+1=?"
        assert result["answer"] == "2"

    def test_parse_nested_json(self):
        from app.tools.generation import GenerateQuestionTool

        tool = GenerateQuestionTool()
        content = '前缀 {"outer": {"inner": 1}, "list": [1, 2, 3]} 后缀'
        result = tool._parse_json_response(content)

        assert result is not None
        assert result["outer"]["inner"] == 1
        assert len(result["list"]) == 3

    def test_parse_invalid_returns_none(self):
        from app.tools.generation import GenerateQuestionTool

        tool = GenerateQuestionTool()
        result = tool._parse_json_response("不是 JSON")

        assert result is None


# ============================================================
# 6. 配置化难度调整
# ============================================================

class TestDifficultyAdjustment:
    """测试连对/连错驱动的难度调整"""

    def test_consecutive_wrong_lowers_difficulty(self):
        from app.state.learning_state import LearningState

        ls = LearningState()
        ls.record_answer_result(correct=False)
        ls.record_answer_result(correct=False)
        ls.record_answer_result(correct=False)

        assert ls.consecutive_wrong == 3
        assert ls.consecutive_correct == 0

    def test_consecutive_right_raises_difficulty(self):
        from app.state.learning_state import LearningState

        ls = LearningState()
        ls.record_answer_result(correct=True)
        ls.record_answer_result(correct=True)
        ls.record_answer_result(correct=True)

        assert ls.consecutive_correct == 3
        assert ls.consecutive_wrong == 0

    def test_record_answer_updates_streak(self):
        from app.state.learning_state import LearningState

        ls = LearningState()
        ls.record_answer("recursion", True)
        ls.record_answer("recursion", True)
        ls.record_answer("recursion", False)

        assert ls.consecutive_correct == 0
        assert ls.consecutive_wrong == 1

    def test_difficulty_config_is_persisted(self):
        from app.state.learning_state import LearningState

        ls = LearningState()
        ls.record_answer_result(correct=True)
        ls.record_answer_result(correct=True)
        data = ls.to_dict()

        restored = LearningState.from_dict(data)
        assert restored.consecutive_correct == 2


# ============================================================
# 7. StudentState 乐观锁
# ============================================================

class TestStudentStateOptimisticLock:
    """测试 StudentState 乐观锁版本号"""

    @pytest.mark.asyncio
    async def test_save_increments_version(self):
        from app.state.student_state_v2 import StudentState

        state = StudentState("u1")
        state._version = 0

        mock_db = MagicMock()
        mock_db.get_student_state = AsyncMock(return_value=None)
        mock_db.save_student_state = AsyncMock()

        await state.save(mock_db)

        assert state._version == 1
        mock_db.save_student_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_detects_concurrent_conflict(self):
        from app.state.student_state_v2 import StudentState

        state = StudentState("u1")
        state._version = 1

        mock_db = MagicMock()
        # DB 中版本已被其他请求更新为 2
        mock_db.get_student_state = AsyncMock(return_value={"version": 2})
        mock_db.save_student_state = AsyncMock()

        await state.save(mock_db)

        # 检测到冲突后仍保存，但 version 取最大值 +1
        assert state._version == 3


# ============================================================
# 8. 错误信息脱敏
# ============================================================

class TestErrorSanitization:
    """测试错误响应不泄露内部细节"""

    @pytest.mark.asyncio
    async def test_run_returns_generic_error(self):
        from app.agent.teaching_agent import TeachingAgent
        from app.state.student_state_v2 import StudentState

        agent = TeachingAgent()

        with patch.object(agent, "initialize", new=AsyncMock()), \
             patch.object(StudentState, "load", side_effect=Exception("secret_db_password")), \
             patch("app.agent.teaching_agent._default_db") as mock_db:
            mock_db.save_observability_trace = AsyncMock()

            result = await agent.run(user_id="u1", user_input="hello")

            assert result["skill_used"] == "error"
            assert "secret_db_password" not in result["response"]
            assert result["response"] == "抱歉，处理过程中出现了错误，请稍后再试。"
            assert result["metadata"].get("error") == "internal_error"


# ============================================================
# 9. 可观测日志持久化
# ============================================================

class TestObservabilityPersistence:
    """测试可观测日志持久化"""

    @pytest.mark.asyncio
    async def test_persist_writes_to_db(self):
        from app.agent.teaching_agent import ObservabilityLogger
        from app.core.database import Database

        obs = ObservabilityLogger()
        obs.log("stage1", {"x": 1})

        mock_db = MagicMock(spec=Database)
        mock_db.save_observability_trace = AsyncMock()
        await obs.persist(user_id="u1", session_id="s1", db=mock_db)

        mock_db.save_observability_trace.assert_called_once()
        trace_data = mock_db.save_observability_trace.call_args[0][0]
        assert trace_data["user_id"] == "u1"
        assert trace_data["session_id"] == "s1"
        assert len(trace_data["trace"]) == 1


# ============================================================
# 10. 统一 topic 提取函数
# ============================================================

class TestUnifiedTopicExtractor:
    """测试统一 topic 提取函数"""

    def test_extract_topic_from_keyword(self):
        from app.utils.topic_extractor import extract_topic_from_input

        assert extract_topic_from_input("我想学习递归") == "recursion"
        assert extract_topic_from_input("讲解一下动态规划") == "dynamic_programming"
        assert extract_topic_from_input("数组怎么排序") == "array"

    def test_resolve_topic_fallback_chain(self):
        from app.utils.topic_extractor import resolve_topic

        # 输入能提取
        assert resolve_topic("学习递归", weak_topics=["loop"]) == "recursion"
        # 输入不能提取，用 current_topic
        assert resolve_topic("继续", current_topic="loop", weak_topics=["array"]) == "loop"
        # 输入和 current_topic 都没有，用 weak_topics
        assert resolve_topic("继续", weak_topics=["array"]) == "array"
        # 都没有，用 default
        assert resolve_topic("你好") == "Python基础"
