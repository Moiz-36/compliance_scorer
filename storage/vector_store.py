# storage/vector_store.py
import chromadb
from sentence_transformers import SentenceTransformer
from core.interfaces import BaseVectorStore
from core.models import DocumentChunk


# In storage/vector_store.py, change this:
# class ChromaVectorStore(BaseVectorStore):
#     def __init__(self, persist_dir: str = "./chroma_db"):

# To this:
class ChromaVectorStore(BaseVectorStore):
    def __init__(self, persist_dir: str = "/tmp/chroma_db"):

     def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

     def add_chunks(self, chunks: list[DocumentChunk], namespace: str) -> None:
        collection = self.client.get_or_create_collection(name=namespace)
        embeddings = self.model.encode([c.content for c in chunks]).tolist()

        collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.content for c in chunks],
            embeddings=embeddings,
            metadatas=[c.metadata for c in chunks],
        )
        
     def clear_namespace(self, namespace: str) -> None:
        try:
            self.client.delete_collection(name=namespace)
        except Exception:
            # Collection didn't exist yet -- nothing to clear
            pass

     def similarity_search(
        self, query: str, namespace: str, k: int = 3
    ) -> list[DocumentChunk]:
        collection = self.client.get_or_create_collection(name=namespace)
        query_emb = self.model.encode([query]).tolist()

        results = collection.query(query_embeddings=query_emb, n_results=k)
        retrieved = []
        if results["documents"]:
            for doc, meta, doc_id in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["ids"][0],
            ):
                retrieved.append(
                    DocumentChunk(chunk_id=doc_id, content=doc, metadata=meta)
                )
    
        return retrieved