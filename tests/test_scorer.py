# tests/test_scorer.py
from core.models import EvaluationResult
from engine.scorer import ComplianceScorer


def test_scorer_calculates_perfect_score():
    # Arrange
    scorer = ComplianceScorer()
    evaluations_by_category = {
        "Data Subject Rights": [
            EvaluationResult(
                requirement_id="GDPR-15",
                requirement_desc="Access Right",
                status="SATISFIED",
                evidence_text="Available",
                confidence_score=0.9,
            )
        ],
        "Transparency & Legal Basis": [
            EvaluationResult(
                requirement_id="GDPR-13",
                requirement_desc="Contact DPO",
                status="SATISFIED",
                evidence_text="dpo@company.com",
                confidence_score=0.95,
            )
        ],
    }

    # Act
    report = scorer.calculate_report("GDPR", evaluations_by_category)

    # Assert
    assert report.category_scores["Data Subject Rights"] == 100.0
    assert report.category_scores["Transparency & Legal Basis"] == 100.0
    assert report.overall_score == 100.0


def test_scorer_calculates_partial_and_missing_mix():
    # Arrange
    scorer = ComplianceScorer()
    evaluations_by_category = {
        "Data Subject Rights": [
            # 1 SATISFIED (1.0), 1 MISSING (0.0) -> Category Score = 50%
            EvaluationResult(
                requirement_id="GDPR-15",
                requirement_desc="Access",
                status="SATISFIED",
                evidence_text="Text",
                confidence_score=0.8,
            ),
            EvaluationResult(
                requirement_id="GDPR-17",
                requirement_desc="Erasure",
                status="MISSING",
                evidence_text=None,
                confidence_score=0.1,
            ),
        ]
    }

    # Act
    report = scorer.calculate_report("GDPR Test", evaluations_by_category)

    # Assert
    assert report.category_scores["Data Subject Rights"] == 50.0
    assert report.overall_score == 50.0