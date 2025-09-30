from fastapi import APIRouter, Depends, HTTPException
from app.models.chat import ChatMessage, ChatResponse
from app.services.flow_service import get_flow_service, FlowService

router=APIRouter(prefix="/flow", tags=["flow"])

@router.post("/start")
async def start_flow(service: FlowService=Depends(get_flow_service)):
    sid=await service.create_session()
    res=await service.get_flow_response(sid)
    return {"session_id": sid, "message": res.message, "current_step": res.current_step, "metadata": res.metadata}

@router.post("/chat/{session_id}")
async def flow_chat(session_id: str, message: ChatMessage, service: FlowService=Depends(get_flow_service)):
    try:
        res=await service.get_flow_response(session_id, message.message)
        return ChatResponse(message=res.message, session_id=session_id, metadata={
            "current_step":res.current_step,"next_step":res.next_step,"validation_error":res.validation_error,
            "summary":res.summary,"is_complete":res.is_complete, **(res.metadata or {})
        })
    except Exception as e:
        raise HTTPException(500, f"Flow chat error: {e}")
