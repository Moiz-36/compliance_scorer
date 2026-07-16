# engine/compliance_evaluator.py
import numpy as np
from sentence_transformers import CrossEncoder
from core.interfaces import BaseComplianceEvaluator
from core.models import ComplianceResult, DocumentChunk


class CrossEncoderComplianceEvaluator(BaseComplianceEvaluator):
    """
    Evaluates policy chunks against GDPR requirements using a Cross-Encoder NLI model.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/nli-deberta-v3-xsmall",
        pass_threshold: float = 0.6,
    ):
        self.model = CrossEncoder(model_name)
        self.pass_threshold = pass_threshold
        # DeBERTa-v3 Label Mapping: 0 = contradiction, 1 = entailment, 2 = neutral
        self.label_mapping = {0: "contradiction", 1: "entailment", 2: "neutral"}

    def evaluate(
        self, requirement_id: str, requirement_desc: str, chunks: list[DocumentChunk]
    ) -> ComplianceResult:
        if not chunks:
            return ComplianceResult(
                requirement_id=requirement_id,
                status="non-compliant",
                score=0.0,
                evidence="No relevant text chunks found in the policy to satisfy this requirement.",
                reasoning="Missing mandatory policy clause.",
            )

        pairs = [(c.content, requirement_desc) for c in chunks]
        scores = self.model.predict(pairs)

        best_entailment_score = -1.0
        best_evidence = ""
        has_contradiction = False

        for idx, score_logits in enumerate(scores):
            probabilities = np.exp(score_logits) / np.sum(np.exp(score_logits))
            pred_label_index = int(np.argmax(probabilities))
            pred_label = self.label_mapping[pred_label_index]
            entailment_prob = float(probabilities[1])

            if pred_label == "contradiction" and probabilities[0] > 0.5:
                has_contradiction = True

            if pred_label == "entailment" and entailment_prob > best_entailment_score:
                best_entailment_score = entailment_prob
                best_evidence = chunks[idx].content

        if has_contradiction:
            return ComplianceResult(
                requirement_id=requirement_id,
                status="non-compliant",
                score=0.0,
                evidence=best_evidence[:200] if best_evidence else "Contradictory clause found.",
                reasoning="The policy directly contradicts this GDPR requirement.",
            )

        if best_entailment_score >= self.pass_threshold:
            return ComplianceResult(
                requirement_id=requirement_id,
                status="compliant",
                score=best_entailment_score,
                evidence=best_evidence[:200],
                reasoning="Requirement satisfied with strong semantic entailment.",
            )

        return ComplianceResult(
            requirement_id=requirement_id,
            status="non-compliant",
            score=0.0,
            evidence="None",
            reasoning="This requirement is missing or unaddressed in the provided text.",
        )