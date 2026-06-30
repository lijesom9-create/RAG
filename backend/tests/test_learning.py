"""
Learning Layer 测试
"""

import pytest
from app.learning.analyzer import LearningAnalyzer
from app.learning.report import LearningReport
from app.models.evaluation import EvaluationRecord
from app.models.learning_insight import LearningInsight
from app.evaluation.metrics import LearningMetrics


class TestLearningAnalyzer:
    """学习分析器测试"""

    def test_create_analyzer(self):
        """创建分析器"""
        analyzer = LearningAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_records(self):
        """分析空记录"""
        analyzer = LearningAnalyzer()
        report = analyzer.analyze_evaluations("user_1", [])
        assert report.user_id == "user_1"
        assert len(report.insights) == 0

    def test_analyze_with_records(self):
        """分析有记录"""
        analyzer = LearningAnalyzer()
        records = [
            EvaluationRecord(
                result_id=f"r{i}",
                user_id="user_1",
                score=0.5,
                metrics=LearningMetrics(
                    total_questions=10,
                    accuracy=0.5,
                    average_mastery=0.4,
                    weak_topics=["递归"],
                ).to_dict(),
            )
            for i in range(5)
        ]
        report = analyzer.analyze_evaluations("user_1", records)
        assert report.user_id == "user_1"
        assert len(report.insights) > 0

    def test_analyze_accuracy_trend_low(self):
        """分析低正确率趋势"""
        analyzer = LearningAnalyzer()
        records = [
            EvaluationRecord(
                result_id=f"r{i}",
                user_id="user_1",
                score=0.3,
            )
            for i in range(5)
        ]
        insight = analyzer._analyze_accuracy_trend("user_1", records)
        assert insight is not None
        assert insight.category == "accuracy"

    def test_analyze_weak_topics(self):
        """分析薄弱知识点"""
        analyzer = LearningAnalyzer()
        metrics_list = [
            LearningMetrics(weak_topics=["递归", "动态规划"]),
        ]
        insights = analyzer._analyze_weak_topics("user_1", metrics_list)
        assert len(insights) == 2

    def test_analyze_emotion(self):
        """分析情绪状态"""
        analyzer = LearningAnalyzer()
        metrics_list = [
            LearningMetrics(
                confidence_level="low",
                frustration_level="high",
            ),
        ]
        insight = analyzer._analyze_emotion("user_1", metrics_list)
        assert insight is not None
        assert insight.category == "emotion"

    def test_generate_summary(self):
        """生成摘要"""
        analyzer = LearningAnalyzer()
        metrics_list = [
            LearningMetrics(
                total_questions=10,
                accuracy=0.8,
                average_mastery=0.7,
                weak_topics=["递归"],
                strong_topics=["循环"],
            ),
        ]
        summary = analyzer._generate_summary(metrics_list)
        assert "80.0%" in summary


class TestLearningReport:
    """学习报告测试"""

    def test_create_report(self):
        """创建报告"""
        report = LearningReport(user_id="user_1")
        assert report.user_id == "user_1"
        assert len(report.insights) == 0

    def test_get_summary(self):
        """获取摘要"""
        report = LearningReport(
            user_id="user_1",
            summary="学习概况",
            recommendations=["建议1", "建议2"],
            insights=[
                LearningInsight(
                    category="accuracy",
                    finding="正确率较低",
                    suggestion="建议降低难度",
                    confidence=0.8,
                ),
            ],
        )
        summary = report.get_summary()
        assert "user_1" in summary
        assert "建议1" in summary
        assert "正确率较低" in summary

    def test_serialization(self):
        """序列化/反序列化"""
        report = LearningReport(
            user_id="user_1",
            summary="测试摘要",
            recommendations=["建议1"],
        )
        data = report.to_dict()
        restored = LearningReport.from_dict(data)
        assert restored.user_id == "user_1"
        assert restored.summary == "测试摘要"
