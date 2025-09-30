from typing import List, Dict
import os, pickle, logging
from datetime import datetime

logger=logging.getLogger(__name__)

class SimpleRAGService:
    def __init__(self):
        self.docs: Dict[str, str]={}
        self.persist="vector_db/simple.pkl"
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.persist):
                with open(self.persist,'rb') as f: self.docs=pickle.load(f)
                logger.info(f"Loaded {len(self.docs)} chunks")
        except Exception as e:
            logger.error(f"Load error: {e}"); self.docs={}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.persist), exist_ok=True)
            with open(self.persist,'wb') as f: pickle.dump(self.docs, f)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def add_documents(self, paths: List[str])->Dict[str,int]:
        import re
        out={}
        for p in paths:
            try:
                text=""
                if p.lower().endswith(".txt"):
                    with open(p, 'r', encoding='utf-8') as f: text=f.read()
                elif p.lower().endswith(".pdf"):
                    try:
                        import PyPDF2
                        with open(p, 'rb') as f:
                            reader=PyPDF2.PdfReader(f)
                            for pg in reader.pages: text += (pg.extract_text() or "") + "\n"
                    except Exception:
                        text=f"PDF {os.path.basename(p)} (install PyPDF2 for full extraction)"
                text=re.sub(r'\s+', ' ', text).strip()
                chunks=[text[i:i+900] for i in range(0, len(text), 900)] if text else []
                base=os.path.basename(p)
                for i,c in enumerate(chunks):
                    self.docs[f"{base}::chunk_{i}"]=c
                out[p]=len(chunks)
                logger.info(f"Indexed {len(chunks)} chunks from {base}")
            except Exception as e:
                logger.error(f"Doc error {p}: {e}"); out[p]=0
        if out: self._save()
        return out

    def query(self, q: str)->str:
        if not self.docs: return "No documents indexed yet. Upload PDF or TXT files first."
        ql=q.lower().split()
        scored=[]
        for k, c in self.docs.items():
            cl=c.lower()
            score=sum(cl.count(w) for w in ql)
            if q.lower() in cl: score+=5
            if score>0: scored.append((score, c, k))
        if not scored: return f"No relevant information found for '{q}'. Try rephrasing."
        scored.sort(key=lambda x: x[0], reverse=True)
        best=" ".join(" ".join(s.split()[:40]) for _, s, _ in scored[:3])
        return best

rag_service=SimpleRAGService()
