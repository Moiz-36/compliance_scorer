# ingestion/raw_text_loader.py
import uuid
from typing import List
from core.interfaces import BaseDocumentLoader
from core.models import DocumentChunk


class RawTextLoader(BaseDocumentLoader):
    """
    Handles raw pasted text input and converts it into DocumentChunks.
    Adheres to Liskov Substitution Principle (LSP).
    """

    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size

    def load(self, file_path: str, source_name: str = "pasted_text") -> List[DocumentChunk]:
        # file_path holds raw pasted text for this loader
        paragraphs = [p.strip() for p in file_path.split("\n\n") if p.strip()]

        chunks = []
        for i, paragraph in enumerate(paragraphs):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{source_name}_chunk_{i+1}_{uuid.uuid4().hex[:6]}",
                    content=paragraph,
                    metadata={"source": source_name, "section_index": i + 1},
                )
            )

        return chunks