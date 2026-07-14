# engine/scorer.py
from typing import List, Dict, Optional
from core.models import EvaluationResult, ComplianceReport


class ComplianceScorer:
    """Calculates category and overall compliance scores from evaluated rules."""

    STATUS_VALUES = {
        "SATISFIED": 1.0,
        "PARTIAL": 0.5,
        "MISSING": 0.0,
    }

    # Default weights are GDPR-specific. Pass a different category_weights
    # dict to the constructor to score other regulations (e.g. DORA) without
    # touching this class at all.
    DEFAULT_GDPR_WEIGHTS = {
        "Data Subject Rights": 0.30,
        "Transparency & Legal Basis": 0.30,
        "Data Retention": 0.20,
        "International Transfers": 0.20,
    }

    def __init__(self, category_weights: Optional[Dict[str, float]] = None):
        self.category_weights = category_weights or self.DEFAULT_GDPR_WEIGHTS

    def calculate_report(
        self,
        regulation_name: str,
        evaluations_by_category: Dict[str, List[EvaluationResult]],
    ) -> ComplianceReport:
        category_scores = {}
        all_evaluations = []

        total_weighted_score = 0.0
        total_weight_applied = 0.0

        for category, evaluations in evaluations_by_category.items():
            all_evaluations.extend(evaluations)
            if not evaluations:
                continue

            cat_sum = sum(self.STATUS_VALUES[e.status] for e in evaluations)
            cat_score = (cat_sum / len(evaluations)) * 100
            category_scores[category] = round(cat_score, 2)

            weight = self.category_weights.get(category, 0.10)
            total_weighted_score += cat_score * weight
            total_weight_applied += weight

        overall_score = (
            round(total_weighted_score / total_weight_applied, 2)
            if total_weight_applied > 0
            else 0.0
        )

        return ComplianceReport(
            regulation_name=regulation_name,
            overall_score=overall_score,
            category_scores=category_scores,
            evaluations=all_evaluations,
        )