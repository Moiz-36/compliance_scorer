# tests/test_evaluator.py
import numpy as np
from unittest.mock import patch
from core.models import DocumentChunk
from engine.compliance_evaluator import CrossEncoderComplianceEvaluator


@patch("engine.compliance_evaluator.CrossEncoder")
def test_evaluator_satisfied_status(mock_cross_encoder_cls):
    # Arrange: Return high entailment probability [contradiction, neutral, entailment]
    mock_model_instance = mock_cross_encoder_cls.return_value
    mock_model_instance.predict.return_value = np.array([[0.05, 0.10, 0.85]])

    evaluator = CrossEncoderComplianceEvaluator()
    candidates = [
        DocumentChunk(
            chunk_id="c1",
            content="Users may request deletion of their data at any time.",
            metadata={},
        )
    ]

    # Act
    result = evaluator.evaluate(
        requirement_id="GDPR-17",
        requirement_desc="Users have the right to request deletion.",
        candidate_chunks=candidates,
    )

    # Assert
    assert result.status == "SATISFIED"
    assert result.evidence_text == "Users may request deletion of their data at any time."
    assert result.confidence_score == 0.85


@patch("engine.compliance_evaluator.CrossEncoder")
def test_evaluator_missing_status_on_empty_candidates(mock_cross_encoder_cls):
    # Arrange
    evaluator = CrossEncoderComplianceEvaluator()

    # Act
    result = evaluator.evaluate(
        requirement_id="GDPR-15",
        requirement_desc="Users can access data.",
        candidate_chunks=[],
    )

    # Assert
    assert result.status == "MISSING"
    assert result.evidence_text is None
    assert result.confidence_score == 0.0