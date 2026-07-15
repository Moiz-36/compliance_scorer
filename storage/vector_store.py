# storage/vector_store.py
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List

from core.interfaces import BaseVectorStore
from core.models import DocumentChunk


class ChromaVectorStore(BaseVectorStore):
    """
    Concrete implementation of BaseVectorStore using ChromaDB.
    Fully implements the abstract interface contract to allow instantiation.
    """

    def __init__(self, persist_dir: str = "/tmp/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def add_chunks(self, chunks: List[DocumentChunk], namespace: str) -> None:
        """Indexes document chunks into a specific namespace/collection."""
        collection = self.client.get_or_create_collection(name=namespace)
        if not chunks:
            return
            
        embeddings = self.model.encode([c.content for c in chunks]).tolist()
        collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.content for c in chunks],
            embeddings=embeddings,
            metadatas=[c.metadata for c in chunks],
        )

    def clear_namespace(self, namespace: str) -> None:
        """Clears the specified collection by deleting it completely."""
        try:
            self.client.delete_collection(name=namespace)
        except Exception:
            # If the collection doesn't exist yet, fail silently and gracefully
            pass

    def similarity_search(
        self, query: str, namespace: str, k: int = 3
    ) -> List[DocumentChunk]:
        """Retrieves top-k semantically relevant chunks."""
        collection = self.client.get_or_create_collection(name=namespace)
        query_emb = self.model.encode([query]).tolist()

        results = collection.query(query_embeddings=query_emb, n_results=k)
        retrieved = []
        
        if results and results.get("documents"):
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
            ids = results["ids"][0]
            for doc, meta, doc_id in zip(documents, metadatas, ids):
                retrieved.append(
                    DocumentChunk(chunk_id=doc_id, content=doc, metadata=meta)
                )
        return retrieved