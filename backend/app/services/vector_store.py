import os
import pickle
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

import logging
logger = logging.getLogger(__name__)

class VectorStore:
    """
    Minimal FAISS vector store wrapper with HuggingFace embeddings.
    """
    def __init__(
        self,
        persist_dir: str = "vector_db/faiss_store",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 900,
        chunk_overlap: int = 150
    ):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.index_path = os.path.join(self.persist_dir, "index.faiss")
        self.store_path = os.path.join(self.persist_dir, "store.pkl")

        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", ".", " "]
        )

        self.vs: Optional[FAISS] = None
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.store_path):
                self.vs = FAISS.load_local(
                    self.persist_dir,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS vector store loaded")
            else:
                self.vs = None
        except Exception as e:
            logger.error(f"Error loading FAISS store: {e}")
            self.vs = None

    def _save(self):
        if not self.vs:
            return
        try:
            self.vs.save_local(self.persist_dir)
            logger.info("FAISS vector store saved")
        except Exception as e:
            logger.error(f"Error saving FAISS store: {e}")

    def _to_documents(self, file_paths: List[str]) -> List[Document]:
        docs: List[Document] = []
        for path in file_paths:
            try:
                ext = os.path.splitext(path.lower())[1]
                if ext == ".txt":
                    loader = TextLoader(path, encoding="utf-8")
                elif ext == ".pdf":
                    loader = PyPDFLoader(path)
                else:
                    logger.warning(f"Unsupported file type for {path}")
                    continue
                file_docs = loader.load()
                docs.extend(file_docs)
            except Exception as e:
                logger.error(f"Failed loading {path}: {e}")
        return docs

    def add_files(self, file_paths: List[str]) -> int:
        raw_docs = self._to_documents(file_paths)
        if not raw_docs:
            return 0
        split_docs = self.text_splitter.split_documents(raw_docs)
        if not split_docs:
            return 0

        if self.vs is None:
            self.vs = FAISS.from_documents(split_docs, self.embeddings)
        else:
            self.vs.add_documents(split_docs)
        self._save()
        return len(split_docs)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.vs:
            return []
        results = self.vs.similarity_search_with_score(query, k=k)
        out = []
        for doc, score in results:
            out.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        return out

    def info(self) -> Dict[str, Any]:
        size = 0
        try:
            if self.vs and hasattr(self.vs, "index"):
                size = int(self.vs.index.ntotal)
        except Exception:
            pass
        return {"ntotal": size, "persist_dir": self.persist_dir}
