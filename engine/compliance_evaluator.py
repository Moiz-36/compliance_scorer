# engine/compliance_evaluator.py
import numpy as np
from typing import List, Tuple
from sentence_transformers import CrossEncoder

from core.interfaces import BaseComplianceEvaluator
from core.models import DocumentChunk, EvaluationResult


class CrossEncoderComplianceEvaluator(BaseComplianceEvaluator):
    """
    Evaluates policy chunks against a GDPR requirement using NLI Cross-Encoders.
    Adheres to Single Responsibility Principle (SRP).
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/nli-deberta-v3-base",
        satisfied_threshold: float = 0.70,
        partial_threshold: float = 0.35,
    ):
        # nli-deberta-v3-base outputs logits for: [0: contradiction, 1: neutral, 2: entailment]
        self.model = CrossEncoder(model_name)
        self.satisfied_threshold = satisfied_threshold
        self.partial_threshold = partial_threshold

    def evaluate(
        self,
        requirement_id: str,
        requirement_desc: str,
        candidate_chunks: List[DocumentChunk],
    ) -> EvaluationResult:
        """Evaluates policy chunks against a GDPR requirement using NLI Cross-Encoders."""
        if not candidate_chunks:
            return EvaluationResult(
                requirement_id=requirement_id,
                requirement_desc=requirement_desc,
                status="MISSING",
                evidence_text=None,
                confidence_score=0.0,
            )

        # Build cross-encoder input pairs: (Premise = Policy Chunk, Hypothesis = Requirement text)
        pairs = [(chunk.content, requirement_desc) for chunk in candidate_chunks]

        probabilities = self.model.predict(pairs, apply_softmax=True)

        best_idx, status, confidence = self._evaluate_probabilities(probabilities)
        best_chunk = candidate_chunks[best_idx]
        evidence = best_chunk.content if status != "MISSING" else None

        return EvaluationResult(
            requirement_id=requirement_id,
            requirement_desc=requirement_desc,
            status=status,
            evidence_text=str(evidence) if evidence is not None else None,
            confidence_score=round(float(confidence), 4),
        )

    def _evaluate_probabilities(
        self, probabilities: np.ndarray
    ) -> Tuple[int, str, float]:
        """Classifies compliance status based on NLI output probabilities."""
        best_idx = 0
        best_status = "MISSING"
        max_confidence = -1.0

        for idx, probs in enumerate(probabilities):
            p_contradiction, p_neutral, p_entailment = probs[0], probs[1], probs[2]

            if p_entailment > max_confidence:
                max_confidence = p_entailment
                best_idx = idx

                if p_entailment >= self.satisfied_threshold:
                    best_status = "SATISFIED"
                elif (
                    p_entailment >= self.partial_threshold
                    or (p_neutral > 0.50 and p_contradiction < 0.30)
                ):
                    best_status = "PARTIAL"
                else:
                    best_status = "MISSING"

        return best_idx, best_status, max_confidence