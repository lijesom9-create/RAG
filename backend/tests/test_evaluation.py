"""
Evaluation Layer 测试
"""

import pytest
from app.evaluation.metrics import MetricsCalculator, LearningMetrics
from app.evaluation.evaluator import Evaluator
from app.evaluation.report import EvaluationReport
from app.models.evaluation import EvaluationRecord


class TestLearningMetrics:
    """学习指标测试"""

    def test_create_metrics(self):
        """创建指标"""
        metrics = LearningMetrics()
        assert metrics.total_questions == 0
        assert metrics.accuracy == 0.0

    def test_serialization(self):
        """序列化/反序列化"""
        metrics = LearningMetrics(
            total_questions=10,
            correct_answers=8,
            accuracy=0.8,
        )
        data = metrics.to_dict()
        restored = LearningMetrics.from_dict(data)
        assert restored.total_questions == 10
        assert restored.accuracy == 0.8


class TestMetricsCalculator:
    """指标计算器测试"""

    def test_calculate_improvement(self):
        """计算进步"""
        calculator = MetricsCalculator()
        current = LearningMetrics(accuracy=0.8, average_mastery=0.7)
        previous = LearningMetrics(accuracy=0.6, average_mastery=0.5)
        improvement = calculator.calculate_improvement(current, previous)
        assert improvement["accuracy_change"] == pytest.approx(0.2)
        assert improvement["mastery_change"] == pytest.approx(0.2)

    def test_identify_patterns_struggling(self):
        """识别困难模式"""
        calculator = MetricsCalculator()
        metrics = LearningMetrics(accuracy=0.3, total_questions=10)
        patterns = calculator.identify_patterns(metrics)
        assert patterns.get("difficulty") == "struggling"

    def test_identify_patterns_excellent(self):
        """识别优秀模式"""
        calculator = MetricsCalculator()
        metrics = LearningMetrics(accuracy=0.9, total_questions=15)
        patterns = calculator.identify_patterns(metrics)
        assert patterns.get("performance") == "excellent"

    def test_identify_patterns_needs_support(self):
        """识别需要支持模式"""
        calculator = MetricsCalculator()
        metrics = LearningMetrics(
            confidence_level="low",
            frustration_level="high",
        )
        patterns = calculator.identify_patterns(metrics)
        assert patterns.get("emotion") == "needs_support"


class TestEvaluator:
    """评估器测试"""

    def test_create_evaluator(self):
        """创建评估器"""
        evaluator = Evaluator()
        assert evaluator is not None

    def test_calculate_score(self):
        """计算分数"""
        evaluator = Evaluator()
        metrics = LearningMetrics(
            accuracy=0.8,
            average_mastery=0.7,
            confidence_level="high",
            frustration_level="low",
            total_interactions=5,
        )
        score = evaluator._calculate_score(metrics, "practice_session")
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # 应该有较高分数

    def test_generate_report(self):
        """生成报告"""
        evaluator = Evaluator()
        records = [
            EvaluationRecord(
                result_id="r1",
                user_id="user_1",
                score=0.8,
                metrics={"accuracy": 0.8, "average_mastery": 0.7},
            ),
        ]
        report = evaluator.generate_report("user_1", records)
        assert report.user_id == "user_1"
        assert report.total_evaluations == 1

    def test_generate_recommendations(self):
        """生成建议"""
        evaluator = Evaluator()
        patterns = {"difficulty": "struggling"}
        metrics = LearningMetrics(weak_topics=["递归"])
        recommendations = evaluator._generate_recommendations(patterns, metrics)
        assert len(recommendations) > 0


class TestEvaluationReport:
    """评估报告测试"""

    def test_create_report(self):
        """创建报告"""
        report = EvaluationReport(user_id="user_1")
        assert report.user_id == "user_1"
        assert report.total_evaluations == 0

    def test_get_summary(self):
        """获取摘要"""
        report = EvaluationReport(
            user_id="user_1",
            total_evaluations=10,
            current_metrics=LearningMetrics(
                accuracy=0.8,
                average_mastery=0.7,
                confidence_level="high",
            ),
        )
        summary = report.get_summary()
        assert "user_1" in summary
        assert "80.0%" in summary

    def test_serialization(self):
        """序列化/反序列化"""
        report = EvaluationReport(
            user_id="user_1",
            total_evaluations=5,
            current_metrics=LearningMetrics(accuracy=0.8),
        )
        data = report.to_dict()
        restored = EvaluationReport.from_dict(data)
        assert restored.user_id == "user_1"
        assert restored.total_evaluations == 5
