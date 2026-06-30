"""
Retrieval Layer 测试
"""

import pytest
from app.retrieval.base import BaseRetriever, RetrievalResult
from app.retrieval.reranker import SimpleReranker, LLMReranker
from app.retrieval.hybrid_search import HybridSearchRetriever


class TestRetrievalResult:
    """检索结果测试"""

    def test_create_result(self):
        """创建检索结果"""
        result = RetrievalResult(
            content="递归是函数调用自身",
            source="course_knowledge",
            score=0.9,
            metadata={"topic": "递归"},
        )
        assert result.content == "递归是函数调用自身"
        assert result.score == 0.9

    def test_to_dict(self):
        """转换为字典"""
        result = RetrievalResult(
            content="内容",
            source="source",
            score=0.8,
        )
        data = result.to_dict()
        assert data["content"] == "内容"
        assert data["score"] == 0.8


class TestSimpleReranker:
    """简单重排序器测试"""

    def test_create_reranker(self):
        """创建重排序器"""
        reranker = SimpleReranker()
        assert reranker.name == "simple_reranker"

    def test_rerank_empty(self):
        """重排序空列表"""
        reranker = SimpleReranker()
        results = reranker.rerank("query", [])
        assert results == []

    def test_rerank_by_score(self):
        """按分数重排序"""
        reranker = SimpleReranker()
        results = [
            RetrievalResult(content="低分", source="source", score=0.3),
            RetrievalResult(content="高分", source="source", score=0.9),
            RetrievalResult(content="中分", source="source", score=0.6),
        ]
        reranked = reranker.rerank("query", results)
        assert reranked[0].content == "高分"
        assert reranked[1].content == "中分"
        assert reranked[2].content == "低分"

    def test_rerank_with_limit(self):
        """重排序并限制数量"""
        reranker = SimpleReranker()
        results = [
            RetrievalResult(content=f"结果{i}", source="source", score=i/10)
            for i in range(10)
        ]
        reranked = reranker.rerank("query", results, limit=3)
        assert len(reranked) == 3

    def test_rerank_by_source(self):
        """按来源重排序"""
        reranker = SimpleReranker(source_weight=1.0, score_weight=0.0)
        results = [
            RetrievalResult(content="课程知识", source="course_knowledge", score=0.5),
            RetrievalResult(content="用户知识", source="user_knowledge", score=0.5),
        ]
        reranked = reranker.rerank("query", results)
        assert reranked[0].source == "course_knowledge"


class TestLLMReranker:
    """LLM 重排序器测试"""

    def test_fallback_to_simple(self):
        """无 LLM 服务时回退到简单重排序"""
        reranker = LLMReranker(llm_service=None)
        results = [
            RetrievalResult(content="低分", source="source", score=0.3),
            RetrievalResult(content="高分", source="source", score=0.9),
        ]
        reranked = reranker.rerank("query", results)
        assert reranked[0].content == "高分"


class MockRetriever(BaseRetriever):
    """模拟检索器"""

    name = "mock"

    def __init__(self, results):
        self.results = results

    async def retrieve(self, query, limit=5, filters=None):
        return self.results[:limit]


class TestHybridSearch:
    """混合检索测试"""

    def test_create_hybrid_search(self):
        """创建混合检索"""
        hybrid = HybridSearchRetriever()
        assert hybrid.name == "hybrid_search"

    @pytest.mark.asyncio
    async def test_retrieve_with_mock(self):
        """使用模拟检索器测试"""
        mock_results = [
            RetrievalResult(content="结果1", source="mock", score=0.9),
            RetrievalResult(content="结果2", source="mock", score=0.7),
        ]
        mock_retriever = MockRetriever(mock_results)
        hybrid = HybridSearchRetriever(vector_retrievers=[mock_retriever])
        results = await hybrid.retrieve("query", limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_deduplicate(self):
        """去重测试"""
        mock_results = [
            RetrievalResult(content="重复内容abc", source="source1", score=0.9),
            RetrievalResult(content="重复内容abc", source="source2", score=0.7),
            RetrievalResult(content="不同内容xyz", source="source1", score=0.8),
        ]
        mock_retriever = MockRetriever(mock_results)
        hybrid = HybridSearchRetriever(vector_retrievers=[mock_retriever])
        results = await hybrid.retrieve("query", limit=5)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_retrievers(self):
        """无检索器时返回空"""
        hybrid = HybridSearchRetriever()
        results = await hybrid.retrieve("query")
        assert results == []
