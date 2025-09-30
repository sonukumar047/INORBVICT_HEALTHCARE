from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid, logging
from enum import Enum
from app.models.flow import FlowData, FlowResponse, FlowStep
from app.utils.validation import ValidationUtils, sanitize_input

logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SessionStatus(Enum):
    ACTIVE="active"; COMPLETED="completed"; EXPIRED="expired"; ERROR="error"

class FlowSession:
    def __init__(self, session_id: str):
        self.session_id=session_id
        self.flow_data=FlowData(step=FlowStep.START)
        self.created_at=datetime.utcnow()
        self.last_activity=datetime.utcnow()
        self.status=SessionStatus.ACTIVE
        self.retry_count=0
        self.history: List[Dict[str, Any]]=[]
        self.metadata: Dict[str, Any]={}
    def touch(self): self.last_activity=datetime.utcnow()
    def expired(self, minutes=30)->bool: return datetime.utcnow()>self.last_activity+timedelta(minutes=minutes)
    def inc_retry(self): self.retry_count+=1
    def reset_retry(self): self.retry_count=0
    def add(self, u, b, step): self.history.append({"ts":datetime.utcnow().isoformat(),"u":u,"b":b,"step":step,"retries":self.retry_count})

class FlowService:
    def __init__(self, timeout=30, max_retries=3):
        self.sessions: Dict[str, FlowSession]={}
        self.timeout=timeout
        self.max_retries=max_retries
        self.messages=self._msgs()
        self.options=['consulting','development','support','training','maintenance']
        logger.info(f"FlowService initialized with {timeout}min timeout, {max_retries} max retries")

    def _msgs(self)->Dict[FlowStep, Dict[str,str]]:
        return {
            FlowStep.START: {"welcome":"👋 Welcome! Let's get started.","prompt":"What's your name?","hint":"Enter at least 2 letters"},
            FlowStep.NAME: {"success":"Nice to meet you, {name}!","prompt":"What's your email address?","hint":"Enter a valid email like user@example.com"},
            FlowStep.EMAIL: {"success":"Got your email {email}.","prompt":"What's your phone number?","hint":"Enter a valid 10-digit number"},
            FlowStep.PHONE: {"success":"Phone saved {phone}.","prompt":"Which service do you need?","hint":f"Choose one: consulting, development, support, training, maintenance"},
            FlowStep.SERVICE: {"success":"Service selected: {service}.","prompt":"Preparing summary...","hint":"Pick a single service from the list"},
            FlowStep.SUMMARY: {"complete":"🎉 Thank you! Here's your summary."}
        }

    async def create_session(self)->str:
        sid=str(uuid.uuid4()); self.sessions[sid]=FlowSession(sid); logger.info(f"Created new session: {sid}"); return sid

    async def _get_or_create(self, sid: str)->FlowSession:
        s=self.sessions.get(sid) or FlowSession(sid); self.sessions[sid]=s
        if s.expired(self.timeout): s.status=SessionStatus.EXPIRED
        return s

    async def get_flow_response(self, sid: str, user_input: str=None)->FlowResponse:
        s=await self._get_or_create(sid)
        if s.status!=SessionStatus.ACTIVE: return await self._inactive(s)
        s.touch()

        if user_input:
            user_input=sanitize_input(user_input)
            err=await self._validate_and_update(s, user_input)
            if err:
                s.add(user_input, err, s.flow_data.step.value); s.inc_retry()
                if s.retry_count>=self.max_retries: return await self._maxed(s)
                return FlowResponse(message=err, current_step=s.flow_data.step.value, validation_error=err, metadata={"retry_count":s.retry_count,"max_retries":self.max_retries})
            s.reset_retry()

        return await self._next(s, user_input)

    async def _inactive(self, s: FlowSession)->FlowResponse:
        if s.status==SessionStatus.EXPIRED:
            s.status=SessionStatus.ACTIVE; s.flow_data=FlowData(step=FlowStep.START); s.reset_retry()
            return FlowResponse(message="Session expired. Let's restart. What's your name?", current_step=FlowStep.NAME.value, next_step=FlowStep.EMAIL.value, metadata={"session_restarted":True})
        if s.status==SessionStatus.COMPLETED:
            return FlowResponse(message="You've completed the flow. Start over?", current_step=FlowStep.END.value, is_complete=True, metadata={"session_completed":True})
        s.status=SessionStatus.ACTIVE; s.flow_data=FlowData(step=FlowStep.START); s.reset_retry()
        return FlowResponse(message="Session reset. What's your name?", current_step=FlowStep.NAME.value, metadata={"session_reset":True})

    async def _maxed(self, s: FlowSession)->FlowResponse:
        prev=s.flow_data.step
        s.flow_data=FlowData(step=FlowStep.START); s.status=SessionStatus.ACTIVE; s.reset_retry()
        return FlowResponse(message="Too many attempts. Let's start fresh. What's your name?", current_step=FlowStep.NAME.value, next_step=FlowStep.EMAIL.value, validation_error="max_retries", metadata={"previous_step":prev.value})

    async def _validate_and_update(self, s: FlowSession, text: str)->Optional[str]:
        fd=s.flow_data; st=fd.step
        if st==FlowStep.NAME:
            v=ValidationUtils.validate_name(text)
            if not v['is_valid']: return f"❌ {v['message']} • {self.messages[FlowStep.NAME]['hint']}"
            fd.name=v['normalized_name']; fd.step=FlowStep.EMAIL; logger.info(f"{s.session_id}: name OK {fd.name}")
        elif st==FlowStep.EMAIL:
            v=ValidationUtils.validate_email(text)
            if not v['is_valid']: return f"❌ {v['message']} • {self.messages[FlowStep.EMAIL]['hint']}"
            fd.email=v['normalized_email']; fd.step=FlowStep.PHONE; logger.info(f"{s.session_id}: email OK {fd.email}")
        elif st==FlowStep.PHONE:
            v=ValidationUtils.validate_phone(text)
            if not v['is_valid']: return f"❌ {v['message']} • {self.messages[FlowStep.PHONE]['hint']}"
            fd.phone=v['formatted_phone'] or text; fd.step=FlowStep.SERVICE; logger.info(f"{s.session_id}: phone OK {fd.phone}")
        elif st==FlowStep.SERVICE:
            v=ValidationUtils.validate_service_selection(text, self.options)
            if not v['is_valid']: return f"❌ {v['message']} • {self.messages[FlowStep.SERVICE]['hint']}"
            fd.service=v['normalized_service']; fd.step=FlowStep.SUMMARY; logger.info(f"{s.session_id}: service OK {fd.service}")
        return None

    async def _next(self, s: FlowSession, user_input: str=None)->FlowResponse:
        fd=s.flow_data; st=fd.step; m=self.messages
        if st==FlowStep.START:
            fd.step=FlowStep.NAME; msg=f"{m[FlowStep.START]['welcome']}\n{m[FlowStep.START]['prompt']}"; s.add("", msg, FlowStep.START.value)
            return FlowResponse(message=msg, current_step=FlowStep.NAME.value, next_step=FlowStep.EMAIL.value, metadata={"hint":m[FlowStep.START]['hint']})
        if st==FlowStep.EMAIL:
            msg=f"{m[FlowStep.NAME]['success'].format(name=fd.name)}\n{m[FlowStep.NAME]['prompt']}"; s.add(user_input or "", msg, st.value)
            return FlowResponse(message=msg, current_step=FlowStep.EMAIL.value, next_step=FlowStep.PHONE.value, metadata={"hint":m[FlowStep.EMAIL]['hint']})
        if st==FlowStep.PHONE:
            msg=f"{m[FlowStep.EMAIL]['success'].format(email=fd.email)}\n{m[FlowStep.EMAIL]['prompt']}"; s.add(user_input or "", msg, st.value)
            return FlowResponse(message=msg, current_step=FlowStep.PHONE.value, next_step=FlowStep.SERVICE.value, metadata={"hint":m[FlowStep.PHONE]['hint']})
        if st==FlowStep.SERVICE:
            services="\n".join(f"• {x.title()}" for x in self.options)
            msg=f"{m[FlowStep.PHONE]['success'].format(phone=fd.phone)}\n{m[FlowStep.PHONE]['prompt']}\n\nAvailable services:\n{services}"
            s.add(user_input or "", msg, st.value)
            return FlowResponse(message=msg, current_step=FlowStep.SERVICE.value, next_step=FlowStep.SUMMARY.value, metadata={"hint":m[FlowStep.SERVICE]['hint'], "options":self.options})
        if st==FlowStep.SUMMARY:
            s.status=SessionStatus.COMPLETED
            summary={"name":fd.name,"email":fd.email,"phone":fd.phone,"service":fd.service,"session_id":s.session_id,"completed_at":datetime.utcnow().isoformat()}
            s.metadata['final_summary']=summary
            msg=f"{m[FlowStep.SERVICE]['success'].format(service=fd.service)}\n\n{m[FlowStep.SUMMARY]['complete']}"
            s.add(user_input or "", msg, st.value)
            return FlowResponse(message=msg, current_step=FlowStep.SUMMARY.value, summary=summary, is_complete=True, metadata={"session_completed":True})
        return FlowResponse(message="Let's start over. What's your name?", current_step=FlowStep.NAME.value, validation_error="unknown_state")
        
flow_service=FlowService()
async def get_flow_service()->FlowService: return flow_service
