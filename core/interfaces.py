from abc import ABC, abstractmethod
from typing import List
from core.models import DocumentChunk, EvaluationResult

class BaseDocumentLoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> List[DocumentChunk]:
        """Reads a document and returns raw chunks."""
        pass

class BaseVectorStore(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk], namespace: str) -> None:
        """Indexes document chunks into a specific namespace/collection."""
        pass

    @abstractmethod
    def similarity_search(self, query: str, namespace: str, k: int = 3) -> List[DocumentChunk]:
        """Retrieves top-k relevant chunks."""
        pass

    @abstractmethod
    def clear_namespace(self, namespace: str) -> None:
        """Removes all indexed chunks from a namespace/collection."""
        pass

class BaseComplianceEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self, requirement_id: str, requirement_desc: str, candidate_chunks: List[DocumentChunk]
    ) -> EvaluationResult:
        """Evaluates whether candidate chunks satisfy a regulation requirement."""
        pass