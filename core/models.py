# core/models.py
from pydantic import BaseModel
from typing import List, Optional, Literal


class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: dict  # Stores document source, article/section number, page number


class EvaluationResult(BaseModel):
    requirement_id: str
    requirement_desc: str
    status: Literal["SATISFIED", "PARTIAL", "MISSING"]
    evidence_text: Optional[str] = None
    confidence_score: float


class ComplianceReport(BaseModel):
    regulation_name: str
    overall_score: float
    category_scores: dict
    evaluations: List[EvaluationResult]