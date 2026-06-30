"""
集成测试 - 验证完整链路

测试场景：递归学科，PracticeSessionSkill
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.agent.teaching_agent import TeachingAgent, ObservabilityLogger
from app.models.lifecycle import AgentStatus
from app.memory.manager import MemoryManager
from app.memory.learning_state import LearningState
from app.evaluation.evaluator import Evaluator
from app.learning.analyzer import LearningAnalyzer
from app.optimization.versioned_config import VersionedConfig
from app.optimization.change_log import ChangeLog
from app.capabilities import get_skill, get_all_skills, get_registry
from app.agent.unified_router import UnifiedRouter, RouterDecision
from app.knowledge.document import KnowledgeDocumentStore, KnowledgeDocument, DocumentType
from app.retrieval.unified_retriever import UnifiedRetriever


class TestObservabilityLogger:
    """可观测日志测试"""

    def test_create_logger(self):
        """创建日志记录器"""
        obs = ObservabilityLogger()
        assert len(obs.logs) == 0

    def test_log_entry(self):
        """记录日志"""
        obs = ObservabilityLogger()
        obs.log("test_stage", {"key": "value"})
        assert len(obs.logs) == 1
        assert obs.logs[0]["stage"] == "test_stage"

    def test_get_trace(self):
        """获取完整链路"""
        obs = ObservabilityLogger()
        obs.log("stage1", {})
        obs.log("stage2", {})
        obs.log("stage3", {})
        trace = obs.get_trace()
        assert len(trace) == 3

    def test_get_summary(self):
        """获取链路摘要"""
        obs = ObservabilityLogger()
        obs.log("stage1", {})
        obs.log("stage2", {})
        summary = obs.get_summary()
        assert "stage1" in summary
        assert "stage2" in summary


class TestSkillRegistry:
    """测试 Skill 注册表"""

    def test_all_skills_registered(self):
        """测试所有 Skill 都已注册"""
        registry = get_registry()
        skills = registry.get_all()
        # 现在有 4 个通用能力
        assert len(skills) == 4

    def test_skill_meta(self):
        """测试 Skill 元数据"""
        skill = get_skill("crawler")
        assert skill is not None
        assert skill.meta.name == "crawler"
        assert skill.meta.category == "data_collection"
        assert len(skill.meta.triggers) > 0

    def test_routing_info(self):
        """测试路由信息生成"""
        registry = get_registry()
        info = registry.get_routing_info()
        assert "crawler" in info
        assert "researcher" in info

    def test_find_by_trigger(self):
        """测试触发词匹配"""
        registry = get_registry()
        skill = registry.find_by_trigger("爬取网页")
        assert skill is not None
        assert skill.name == "crawler"


class TestUnifiedRouter:
    """测试统一路由器"""

    def test_answer_submission(self):
        """测试答案提交检测"""
        router = UnifiedRouter()
        result = router._try_answer_submission("A")
        assert result is not None
        assert result.skill_name == "answer_feedback"
        assert result.is_answer_submission is True

    def test_react_trigger(self):
        """测试 ReAct 触发词"""
        router = UnifiedRouter()
        result = router._route_by_trigger("帮我分析一下学习情况")
        assert result is not None
        assert result.is_react is True


class TestMemoryManager:
    """测试 MemoryManager"""

    def test_create_memory_manager(self):
        """测试创建 MemoryManager"""
        mm = MemoryManager("test_user")
        assert mm.user_id == "test_user"
        assert mm.long_term_memory is not None
        assert mm.user_profile is not None
        assert mm.learning_state is not None

    def test_learning_state(self):
        """测试学习状态"""
        ls = LearningState("test_user")
        ls.update_from_interaction("递归", True, "什么是递归？")
        assert ls.get_mastery("递归") == 0.6
        assert "递归" in ls.learned_topics

    def test_learning_state_weak_topic(self):
        """测试薄弱主题识别"""
        ls = LearningState("test_user")
        # 答错多次，掌握度降低
        for _ in range(5):
            ls.update_from_interaction("递归", False, "什么是递归？")
        assert "递归" in ls.weak_topics

    def test_build_context_for_llm(self):
        """测试 LLM 上下文构建"""
        mm = MemoryManager("test_user")
        mm.long_term_memory.update_preference("style", "example_first")
        context = mm.build_context_for_llm()
        assert "example_first" in context


class TestKnowledgeDocument:
    """测试知识文档"""

    def test_create_document(self):
        """测试创建文档"""
        doc = KnowledgeDocument(
            id="test_1",
            title="递归函数",
            content="递归是一种函数调用自身的编程技术。",
            type=DocumentType.COURSE,
            metadata={"topic": "递归", "difficulty": "hard"},
        )
        assert doc.id == "test_1"
        assert doc.get_difficulty() == "hard"

    def test_document_chunks(self):
        """测试文档分块"""
        doc = KnowledgeDocument(
            id="test_1",
            title="递归函数",
            content="递归是一种函数调用自身的编程技术。",
            type=DocumentType.COURSE,
            chunks=["递归是一种函数调用自身的编程技术", "递归函数必须有基准情况"],
        )
        chunks = doc.get_chunks()
        assert len(chunks) == 2

    def test_document_prerequisites(self):
        """测试前置知识"""
        doc = KnowledgeDocument(
            id="test_1",
            title="递归函数",
            content="递归是一种函数调用自身的编程技术。",
            type=DocumentType.COURSE,
            metadata={"prerequisite": ["functions", "loops"]},
        )
        prereqs = doc.get_prerequisites()
        assert "functions" in prereqs
        assert "loops" in prereqs


class TestUnifiedRetriever:
    """测试统一检索器"""

    def test_keyword_search(self):
        """测试关键词搜索"""
        store = KnowledgeDocumentStore()
        doc = KnowledgeDocument(
            id="test_1",
            title="递归函数",
            content="递归是一种函数调用自身的编程技术。",
            type=DocumentType.COURSE,
            metadata={"topic": "递归"},
        )
        store._documents[doc.id] = doc

        retriever = UnifiedRetriever(store)

        # 测试同步搜索
        results = asyncio.run(retriever.search("递归", limit=5))
        assert len(results) > 0
        assert results[0].document.title == "递归函数"

    def test_type_filter(self):
        """测试类型过滤"""
        store = KnowledgeDocumentStore()
        doc1 = KnowledgeDocument(
            id="test_1",
            title="递归函数",
            content="递归是一种函数调用自身的编程技术。",
            type=DocumentType.COURSE,
        )
        doc2 = KnowledgeDocument(
            id="test_2",
            title="递归教学经验",
            content="教递归时应该先讲例子。",
            type=DocumentType.TEACHING,
        )
        store._documents[doc1.id] = doc1
        store._documents[doc2.id] = doc2

        retriever = UnifiedRetriever(store)

        # 按类型过滤
        results = asyncio.run(retriever.search("递归", type_filter=["course"], limit=5))
        assert len(results) == 1
        assert results[0].document.type == DocumentType.COURSE


class TestTeachingAgentIntegration:
    """TeachingAgent 集成测试"""

    def test_agent_initialization(self):
        """Agent 初始化"""
        agent = TeachingAgent()
        assert agent.evaluator is not None
        assert agent.learning_analyzer is not None
        assert agent.versioned_config is not None
        assert agent.change_log is not None
        assert agent.rollback_manager is not None

    def test_default_config(self):
        """默认配置"""
        agent = TeachingAgent()
        config = agent.versioned_config.get_current()
        assert config is not None
        assert "difficulty_adjustment" in config
        assert config["difficulty_adjustment"]["consecutive_wrong_threshold"] == 2
        assert config["difficulty_adjustment"]["consecutive_right_threshold"] == 3

    def _make_state_mock(self, mastery: float = 0.5) -> MagicMock:
        """构造兼容新难度策略的 state mock"""
        state = MagicMock()
        state.current_topic = "递归"
        state.get_mastery.return_value = mastery
        state.learning.consecutive_wrong = 0
        state.learning.consecutive_correct = 0
        return state

    def test_get_recommended_difficulty_easy(self):
        """推荐难度：掌握度低 → easy"""
        agent = TeachingAgent()
        state = self._make_state_mock(mastery=0.2)
        config = {"default_difficulty": "medium"}
        difficulty = agent._get_recommended_difficulty(state, config)
        assert difficulty == "easy"

    def test_get_recommended_difficulty_hard(self):
        """推荐难度：掌握度高 → hard"""
        agent = TeachingAgent()
        state = self._make_state_mock(mastery=0.8)
        config = {"default_difficulty": "medium"}
        difficulty = agent._get_recommended_difficulty(state, config)
        assert difficulty == "hard"

    def test_get_recommended_difficulty_medium(self):
        """推荐难度：掌握度中等 → medium"""
        agent = TeachingAgent()
        state = self._make_state_mock(mastery=0.5)
        config = {"default_difficulty": "medium"}
        difficulty = agent._get_recommended_difficulty(state, config)
        assert difficulty == "medium"


class TestFullChainMock:
    """完整链路模拟测试"""

    @pytest.mark.asyncio
    async def test_full_chain_with_mock(self):
        """完整链路模拟（使用 mock）"""
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
        mock_db.get_session_memory.return_value = None
        mock_db.save_session_memory.return_value = None
        mock_db.get_learning_state.return_value = None
        mock_db.save_learning_state.return_value = None

        # 模拟 Skill
        mock_skill = AsyncMock()
        mock_skill.name = "practice_session"
        mock_skill.triggers = ["练习", "出题"]
        mock_skill.execute.return_value = MagicMock(
            content="这是一道递归题...",
            skill_name="practice_session",
            should_continue=True,
            metadata={"question_id": "q1"},
        )

        # 模拟路由器
        mock_router = AsyncMock()
        mock_router.route.return_value = RouterDecision(
            skill_name="practice_session",
            topic="递归",
            reasoning="测试",
            is_react=False,
        )

        with patch("app.agent.teaching_agent._default_db", mock_db):
            agent = TeachingAgent()
            agent.router = mock_router

            # 模拟 get_skill
            with patch("app.agent.teaching_agent.get_skill", return_value=mock_skill):
                result = await agent.run(
                    user_id="test_user",
                    user_input="给我出一道递归题",
                    session_id="test_session",
                )

                # 验证响应结构
                assert "response" in result
                assert "skill_used" in result
                assert "lifecycle" in result
                assert "observability" in result

                # 验证生命周期状态
                assert result["lifecycle"]["status"] == AgentStatus.COMPLETED.value

                # 验证可观测日志
                assert "trace" in result["observability"]
                assert "summary" in result["observability"]
                assert len(result["observability"]["trace"]) > 0

                # 验证链路包含关键阶段
                summary = result["observability"]["summary"]
                assert "start" in summary
                assert "load_state" in summary
                assert "policy" in summary
                assert "routing" in summary
                assert "execute" in summary
                assert "state_update" in summary
                assert "memory" in summary
                assert "evaluation" in summary


class TestLearningEvaluationChain:
    """Learning + Evaluation 链路测试"""

    def test_evaluation_to_learning(self):
        """Evaluation → Learning 链路"""
        evaluator = Evaluator()
        analyzer = LearningAnalyzer()

        # 模拟评估记录
        from app.models.evaluation import EvaluationRecord
        from app.evaluation.metrics import LearningMetrics

        records = [
            EvaluationRecord(
                result_id=f"r{i}",
                user_id="user_1",
                score=0.3,
                metrics=LearningMetrics(
                    total_questions=10,
                    accuracy=0.3,
                    average_mastery=0.25,
                    weak_topics=["递归"],
                    confidence_level="low",
                    frustration_level="high",
                ).to_dict(),
            )
            for i in range(5)
        ]

        # 生成学习报告
        report = analyzer.analyze_evaluations("user_1", records)

        # 验证报告
        assert report.user_id == "user_1"
        assert len(report.insights) > 0
        assert len(report.recommendations) > 0

        # 验证包含递归相关的洞察
        recursion_insights = [i for i in report.insights if "递归" in i.finding]
        assert len(recursion_insights) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
