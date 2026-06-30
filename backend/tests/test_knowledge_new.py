"""
新知识库架构单元测试
"""

import pytest
from app.knowledge.document import KnowledgeDocument, KnowledgeDocumentStore, DocumentType


class TestKnowledgeDocument:
    """测试 KnowledgeDocument"""

    def test_create_document(self):
        """测试创建文档"""
        doc = KnowledgeDocument(
            id="test_001",
            title="递归函数",
            content="递归是函数调用自身...",
            type=DocumentType.COURSE,
            source="python_basics",
            metadata={"difficulty": "medium", "tags": ["递归"]},
        )

        assert doc.id == "test_001"
        assert doc.title == "递归函数"
        assert doc.type == DocumentType.COURSE
        assert doc.metadata["difficulty"] == "medium"

    def test_to_dict(self):
        """测试序列化"""
        doc = KnowledgeDocument(
            id="test_001",
            title="递归函数",
            content="递归是函数调用自身...",
            type=DocumentType.COURSE,
        )

        data = doc.to_dict()
        assert data["id"] == "test_001"
        assert data["type"] == "course"

    def test_from_dict(self):
        """测试反序列化"""
        data = {
            "id": "test_001",
            "title": "递归函数",
            "content": "递归是函数调用自身...",
            "type": "course",
            "metadata": {"difficulty": "medium"},
        }

        doc = KnowledgeDocument.from_dict(data)
        assert doc.id == "test_001"
        assert doc.type == DocumentType.COURSE

    def test_chunks(self):
        """测试分块"""
        doc = KnowledgeDocument(
            id="test_001",
            title="递归函数",
            content="递归是函数调用自身...",
            type=DocumentType.COURSE,
            chunks=["分块1", "分块2", "分块3"],
        )

        assert len(doc.get_chunks()) == 3
        assert doc.get_chunks()[0] == "分块1"

    def test_chunks_empty(self):
        """测试空分块"""
        doc = KnowledgeDocument(
            id="test_001",
            title="递归函数",
            content="递归是函数调用自身...",
            type=DocumentType.COURSE,
        )

        # 没有分块时返回完整内容
        assert len(doc.get_chunks()) == 1
        assert doc.get_chunks()[0] == "递归是函数调用自身..."

    def test_metadata_helpers(self):
        """测试元数据辅助方法"""
        doc = KnowledgeDocument(
            id="test_001",
            title="递归函数",
            content="...",
            type=DocumentType.COURSE,
            metadata={
                "prerequisite": ["函数", "循环"],
                "related": ["栈", "DFS"],
                "tags": ["递归", "算法"],
                "difficulty": "medium",
            },
        )

        assert doc.get_prerequisites() == ["函数", "循环"]
        assert doc.get_related() == ["栈", "DFS"]
        assert doc.get_tags() == ["递归", "算法"]
        assert doc.get_difficulty() == "medium"


class TestKnowledgeDocumentStore:
    """测试 KnowledgeDocumentStore"""

    @pytest.fixture
    def store(self):
        """创建测试用的存储"""
        return KnowledgeDocumentStore()

    @pytest.fixture
    def sample_docs(self):
        """创建测试文档"""
        return [
            KnowledgeDocument(
                id="kp_recursion",
                title="递归函数",
                content="递归是函数调用自身...",
                type=DocumentType.COURSE,
                source="python_basics",
                metadata={"topic": "递归", "difficulty": "medium", "tags": ["递归", "算法"]},
            ),
            KnowledgeDocument(
                id="exp_recursion",
                title="递归教学经验",
                content="教递归时应该先...",
                type=DocumentType.TEACHING,
                source="teaching_knowledge",
                metadata={"topic": "递归", "category": "best_practice"},
            ),
            KnowledgeDocument(
                id="user_notes",
                title="递归学习笔记",
                content="递归的三要素...",
                type=DocumentType.USER,
                source="user:user_001",
                metadata={"topic": "递归", "user_id": "user_001"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_add_and_get(self, store, sample_docs):
        """测试添加和获取"""
        for doc in sample_docs:
            await store.add_document(doc)

        assert len(store._documents) == 3

        doc = await store.get_document("kp_recursion")
        assert doc is not None
        assert doc.title == "递归函数"

    @pytest.mark.asyncio
    async def test_delete(self, store, sample_docs):
        """测试删除"""
        for doc in sample_docs:
            await store.add_document(doc)

        success = await store.delete_document("kp_recursion")
        assert success is True
        assert len(store._documents) == 2

        doc = await store.get_document("kp_recursion")
        assert doc is None

    @pytest.mark.asyncio
    async def test_search(self, store, sample_docs):
        """测试搜索"""
        for doc in sample_docs:
            await store.add_document(doc)

        results = await store.search("递归")
        assert len(results) == 3

        # 按类型过滤
        results = await store.search("递归", type_filter=["course"])
        assert len(results) == 1
        assert results[0].id == "kp_recursion"

    @pytest.mark.asyncio
    async def test_get_by_type(self, store, sample_docs):
        """测试按类型获取"""
        for doc in sample_docs:
            await store.add_document(doc)

        course_docs = await store.get_by_type("course")
        assert len(course_docs) == 1

        teaching_docs = await store.get_by_type("teaching")
        assert len(teaching_docs) == 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, store, sample_docs):
        """测试统计"""
        for doc in sample_docs:
            await store.add_document(doc)

        stats = await store.get_statistics()
        assert stats["total"] == 3
        assert stats["by_type"]["course"] == 1
        assert stats["by_type"]["teaching"] == 1
        assert stats["by_type"]["user"] == 1


class TestDocumentType:
    """测试 DocumentType"""

    def test_values(self):
        """测试类型值"""
        assert DocumentType.COURSE.value == "course"
        assert DocumentType.TEACHING.value == "teaching"
        assert DocumentType.USER.value == "user"
        assert DocumentType.NOTE.value == "note"
        assert DocumentType.FAQ.value == "faq"
