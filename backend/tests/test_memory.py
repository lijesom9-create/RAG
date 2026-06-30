"""
Memory Layer 测试
"""

import pytest
from app.memory.session_memory import SessionMemory
from app.memory.long_term_memory import LongTermMemory
from app.memory.user_profile import UserProfile
from app.memory.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.memory.manager import MemoryManager


class TestSessionMemory:
    """会话记忆测试"""

    def test_create_session_memory(self):
        """创建会话记忆"""
        memory = SessionMemory(session_id="session_1")
        assert memory.session_id == "session_1"
        assert memory.current_topic is None
        assert memory.recent_qa_pairs == []

    def test_set_topic(self):
        """设置主题"""
        memory = SessionMemory(session_id="session_1")
        memory.set_topic("递归")
        assert memory.current_topic == "递归"

    def test_add_qa_pair(self):
        """添加问答对"""
        memory = SessionMemory(session_id="session_1")
        memory.add_qa_pair("什么是递归？", "递归是...", "concept_lesson")
        assert len(memory.recent_qa_pairs) == 1
        assert memory.recent_qa_pairs[0]["question"] == "什么是递归？"

    def test_max_recent_pairs(self):
        """问答对数量限制"""
        memory = SessionMemory(session_id="session_1")
        memory._max_recent_pairs = 3
        for i in range(5):
            memory.add_qa_pair(f"问题{i}", f"回答{i}")
        assert len(memory.recent_qa_pairs) == 3

    def test_add_emotion(self):
        """添加情绪记录"""
        memory = SessionMemory(session_id="session_1")
        memory.add_emotion("confident", 0.8)
        assert len(memory.emotion_history) == 1

    def test_get_recent_context(self):
        """获取最近上下文"""
        memory = SessionMemory(session_id="session_1")
        memory.set_topic("递归")
        memory.add_qa_pair("问题", "回答")
        context = memory.get_recent_context()
        assert "递归" in context
        assert "问题" in context

    def test_serialization(self):
        """序列化/反序列化"""
        memory = SessionMemory(session_id="session_1")
        memory.set_topic("递归")
        memory.add_qa_pair("问题", "回答")
        data = memory.to_dict()
        restored = SessionMemory.from_dict(data)
        assert restored.session_id == "session_1"
        assert restored.current_topic == "递归"
        assert len(restored.recent_qa_pairs) == 1


class TestLongTermMemory:
    """长期记忆测试"""

    def test_create_memory(self):
        """创建长期记忆"""
        memory = LongTermMemory(user_id="user_1")
        assert memory.user_id == "user_1"
        assert memory.preferences == {}

    def test_update_preference(self):
        """更新偏好"""
        memory = LongTermMemory(user_id="user_1")
        memory.update_preference("learning_style", "visual")
        assert memory.get_preference("learning_style") == "visual"

    def test_add_key_concept(self):
        """添加重要知识点"""
        memory = LongTermMemory(user_id="user_1")
        memory.add_key_concept("递归", "函数调用自身", "high")
        assert len(memory.key_concepts) == 1
        assert memory.key_concepts[0]["concept"] == "递归"

    def test_add_milestone(self):
        """添加里程碑"""
        memory = LongTermMemory(user_id="user_1")
        memory.add_milestone("掌握递归", "能够独立解决递归问题")
        assert len(memory.milestones) == 1

    def test_forget(self):
        """遗忘记忆"""
        memory = LongTermMemory(user_id="user_1")
        memory.update_preference("style", "visual")
        assert memory.forget("preferences", "style")
        assert memory.get_preference("style") is None

    def test_to_prompt(self):
        """转换为 Prompt"""
        memory = LongTermMemory(user_id="user_1")
        memory.update_preference("style", "visual")
        prompt = memory.to_prompt()
        assert "style" in prompt

    def test_serialization(self):
        """序列化/反序列化"""
        memory = LongTermMemory(user_id="user_1")
        memory.update_preference("style", "visual")
        memory.add_key_concept("递归", "函数调用自身")
        data = memory.to_dict()
        restored = LongTermMemory.from_dict(data)
        assert restored.user_id == "user_1"
        assert restored.get_preference("style") == "visual"
        assert len(restored.key_concepts) == 1


class TestUserProfile:
    """用户画像测试"""

    def test_create_profile(self):
        """创建用户画像"""
        profile = UserProfile(user_id="user_1")
        assert profile.user_id == "user_1"
        assert profile.basic_info["major"] == ""

    def test_update_basic_info(self):
        """更新基本信息"""
        profile = UserProfile(user_id="user_1")
        profile.update_basic_info("major", "计算机科学")
        assert profile.get_basic_info("major") == "计算机科学"

    def test_learning_style(self):
        """学习风格"""
        profile = UserProfile(user_id="user_1")
        profile.update_learning_style("visual", 0.8)
        profile.update_learning_style("auditory", 0.3)
        assert profile.get_dominant_style() == "visual"

    def test_goals(self):
        """学习目标"""
        profile = UserProfile(user_id="user_1")
        profile.add_short_term_goal("掌握递归", "本周")
        profile.add_long_term_goal("通过考试", "期末")
        assert len(profile.short_term_goals) == 1
        assert len(profile.long_term_goals) == 1

    def test_stats(self):
        """学习统计"""
        profile = UserProfile(user_id="user_1")
        profile.update_stats("total_questions", 10)
        profile.increment_stats("correct_answers", 8)
        assert profile.get_accuracy() == 0.8

    def test_serialization(self):
        """序列化/反序列化"""
        profile = UserProfile(user_id="user_1")
        profile.update_basic_info("major", "计算机科学")
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)
        assert restored.get_basic_info("major") == "计算机科学"


class TestKnowledgeBase:
    """知识库测试"""

    def test_create_kb(self):
        """创建知识库"""
        kb = KnowledgeBase(user_id="user_1")
        assert kb.user_id == "user_1"
        assert len(kb.documents) == 0

    def test_add_document(self):
        """添加文档"""
        kb = KnowledgeBase(user_id="user_1")
        doc = KnowledgeDocument(
            doc_id="doc_1",
            title="递归笔记",
            content="递归是函数调用自身",
        )
        kb.add_document(doc)
        assert len(kb.documents) == 1

    def test_get_document(self):
        """获取文档"""
        kb = KnowledgeBase(user_id="user_1")
        doc = KnowledgeDocument(doc_id="doc_1", title="笔记", content="内容")
        kb.add_document(doc)
        retrieved = kb.get_document("doc_1")
        assert retrieved is not None
        assert retrieved.title == "笔记"

    def test_delete_document(self):
        """删除文档"""
        kb = KnowledgeBase(user_id="user_1")
        doc = KnowledgeDocument(doc_id="doc_1", title="笔记", content="内容")
        kb.add_document(doc)
        assert kb.delete_document("doc_1")
        assert len(kb.documents) == 0

    def test_search_by_keyword(self):
        """按关键词搜索"""
        kb = KnowledgeBase(user_id="user_1")
        kb.add_document(KnowledgeDocument(
            doc_id="doc_1", title="递归笔记", content="递归是函数调用自身"
        ))
        kb.add_document(KnowledgeDocument(
            doc_id="doc_2", title="循环笔记", content="for循环"
        ))
        results = kb.search_by_keyword("递归")
        assert len(results) == 1
        assert results[0].doc_id == "doc_1"

    def test_serialization(self):
        """序列化/反序列化"""
        kb = KnowledgeBase(user_id="user_1")
        kb.add_document(KnowledgeDocument(
            doc_id="doc_1", title="笔记", content="内容"
        ))
        data = kb.to_dict()
        restored = KnowledgeBase.from_dict(data)
        assert len(restored.documents) == 1


class TestMemoryManager:
    """记忆管理器测试"""

    def test_create_manager(self):
        """创建管理器"""
        manager = MemoryManager(user_id="user_1")
        assert manager.user_id == "user_1"
        assert manager.session_memory is None

    def test_init_session(self):
        """初始化会话"""
        manager = MemoryManager(user_id="user_1")
        manager.init_session("session_1")
        assert manager.session_memory is not None
        assert manager.session_memory.session_id == "session_1"

    def test_store_session_qa(self):
        """存储会话问答"""
        manager = MemoryManager(user_id="user_1")
        manager.init_session("session_1")
        manager.store_session_qa("问题", "回答", "skill")
        assert len(manager.session_memory.recent_qa_pairs) == 1

    def test_store_preference(self):
        """存储偏好"""
        manager = MemoryManager(user_id="user_1")
        manager.store_preference("style", "visual")
        assert manager.long_term_memory.get_preference("style") == "visual"

    def test_forget_preference(self):
        """遗忘偏好"""
        manager = MemoryManager(user_id="user_1")
        manager.store_preference("style", "visual")
        assert manager.forget_preference("style")
        assert manager.long_term_memory.get_preference("style") is None

    def test_build_context_for_llm(self):
        """构建 LLM 上下文"""
        manager = MemoryManager(user_id="user_1")
        manager.update_profile("major", "计算机科学")
        manager.store_preference("style", "visual")
        context = manager.build_context_for_llm()
        assert "计算机科学" in context

    def test_serialization(self):
        """序列化/反序列化"""
        manager = MemoryManager(user_id="user_1")
        manager.store_preference("style", "visual")
        manager.update_profile("major", "计算机科学")
        data = manager.to_dict()
        restored = MemoryManager.from_dict(data)
        assert restored.user_id == "user_1"
        assert restored.long_term_memory.get_preference("style") == "visual"
