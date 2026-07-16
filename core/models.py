# core/models.py
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceResult(BaseModel):
    requirement_id: str
    status: str  # "compliant" or "non-compliant"
    score: float
    evidence: Optional[str] = "None"
    reasoning: Optional[str] = ""


# Alias to support any interface/evaluator importing EvaluationResult
EvaluationResult = ComplianceResult