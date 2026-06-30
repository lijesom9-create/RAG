"""
学习路径服务测试
"""

import pytest
from unittest.mock import MagicMock

from app.knowledge.graph import KnowledgeGraph, KnowledgeNode, KnowledgeEdge
from app.services.learning_path import LearningPathService


@pytest.fixture
def sample_graph():
    """预置知识图谱"""
    graph = KnowledgeGraph()
    nodes = [
        KnowledgeNode("variables", "变量", "变量定义", "easy", "基础"),
        KnowledgeNode("functions", "函数", "函数定义", "medium", "基础"),
        KnowledgeNode("recursion", "递归", "递归函数", "hard", "算法"),
    ]
    for n in nodes:
        graph.add_node(n)

    graph.add_edge(KnowledgeEdge("variables", "functions", "prerequisite"))
    graph.add_edge(KnowledgeEdge("functions", "recursion", "prerequisite"))

    return graph


class TestLearningPathService:
    """学习路径服务测试"""

    def test_generate_path_returns_ordered_nodes(self, sample_graph):
        """生成的路径按前置知识排序"""
        service = LearningPathService(sample_graph)
        state = MagicMock()
        state.get_mastery.return_value = 0.0
        state.get_weak_topics.return_value = []

        path = service.generate_path("递归", state)

        assert path.target_topic == "递归"
        assert len(path.nodes) == 3
        assert [n.topic for n in path.nodes] == ["变量", "函数", "递归"]

    def test_generate_path_respects_mastery(self, sample_graph):
        """已掌握知识点状态为 mastered"""
        service = LearningPathService(sample_graph)
        state = MagicMock()

        def mastery(topic):
            return {"变量": 0.9, "函数": 0.5, "递归": 0.0}.get(topic, 0.0)

        state.get_mastery.side_effect = mastery
        state.get_weak_topics.return_value = []

        path = service.generate_path("递归", state)

        statuses = {n.topic: n.status for n in path.nodes}
        assert statuses["变量"] == "mastered"
        assert statuses["函数"] == "learning"
        assert statuses["递归"] == "blocked"  # 前置未完全掌握

    def test_recommend_next_from_weak_topics(self, sample_graph):
        """基于薄弱点推荐下一步"""
        service = LearningPathService(sample_graph)
        state = MagicMock()
        state.get_mastery.return_value = 0.0
        state.get_weak_topics.return_value = ["递归"]

        next_node = service.recommend_next(state)

        assert next_node is not None
        assert next_node.topic == "变量"  # 递归路径的第一个节点

    def test_generate_path_unknown_topic(self, sample_graph):
        """未知主题返回空路径"""
        service = LearningPathService(sample_graph)
        state = MagicMock()

        path = service.generate_path("量子力学", state)

        assert len(path.nodes) == 0
        assert "未找到知识点" in path.summary
