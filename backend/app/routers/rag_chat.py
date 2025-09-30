from fastapi import APIRouter, File, UploadFile, HTTPException
from app.models.chat import ChatMessage, ChatResponse
from app.services.rag_service import rag_service
from typing import List
import uuid, os, logging

logger=logging.getLogger(__name__)
router=APIRouter(prefix="/rag", tags=["rag"])

@router.post("/start")
async def start_rag():
    sid=str(uuid.uuid4())
    return {"session_id":sid, "message":"RAG ready. Upload documents using the button above, then ask questions.", "mode":"rag"}

@router.post("/upload")
async def upload(files: List[UploadFile]=File(...)):
    if not files: raise HTTPException(400, "No files uploaded")
    saved=[]
    os.makedirs("data/documents", exist_ok=True)
    errors=[]
    for f in files:
        try:
            if f.content_type not in ["application/pdf","text/plain"]:
                errors.append(f"Invalid type {f.filename}: {f.content_type}"); continue
            data=await f.read()
            if len(data)>10*1024*1024: errors.append(f"Too large {f.filename}"); continue
            safe="".join(ch for ch in f.filename if ch.isalnum() or ch in ".-_")
            path=os.path.join("data/documents", safe or f"file_{uuid.uuid4().hex}.bin")
            if f.content_type=="text/plain":
                try:
                    text=data.decode("utf-8")
                except UnicodeDecodeError:
                    text=data.decode("latin-1", errors="ignore")
                with open(path, "w", encoding="utf-8") as fh: fh.write(text)
            else:
                with open(path, "wb") as fh: fh.write(data)
            saved.append(path)
            logger.info(f"Saved {path}")
        except Exception as e:
            errors.append(f"{f.filename}: {e}")
    if not saved and errors: raise HTTPException(400, f"Upload errors: {'; '.join(errors)}")
    results=rag_service.add_documents(saved)
    return {"message":"Uploaded", "processed_files":results, "total_chunks":sum(results.values()), "errors": errors or None}

@router.post("/chat/{session_id}")
async def rag_chat(session_id: str, message: ChatMessage):
    try:
        ans=rag_service.query(message.message)
        return ChatResponse(message=ans, session_id=session_id, metadata={"mode":"rag"})
    except Exception as e:
        raise HTTPException(500, f"RAG chat error: {e}")
