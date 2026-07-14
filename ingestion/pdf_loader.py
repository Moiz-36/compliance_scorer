
import pypdf
from core.interfaces import BaseDocumentLoader
from core.models import DocumentChunk

class PDFLoader(BaseDocumentLoader):
    def load(self, file_path: str) -> list[DocumentChunk]:
        reader = pypdf.PdfReader(file_path)
        chunks = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{file_path}_p{i+1}",
                        content=text,
                        metadata={"source": file_path, "page": i + 1}
                    )
                )
        return chunks