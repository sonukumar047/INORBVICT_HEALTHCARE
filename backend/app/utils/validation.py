import re
from typing import Dict, Any

def sanitize_input(text: str) -> str:
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', text)
    return ' '.join(text.split()).strip()

class ValidationUtils:
    @staticmethod
    def validate_name(name: str) -> Dict[str, Any]:
        res={'is_valid': False, 'message':'', 'normalized_name': None}
        if not name: res['message']='Name is required'; return res
        name=name.strip()
        if len(name)<2: res['message']='Name must be at least 2 characters'; return res
        if not re.fullmatch(r"[a-zA-Z\s\-']{2,50}", name): res['message']='Only letters, spaces, hyphens, apostrophes allowed'; return res
        res['is_valid']=True; res['normalized_name']=' '.join(w.capitalize() for w in name.split()); res['message']='OK'; return res

    @staticmethod
    def validate_email(email: str, strict: bool=False) -> Dict[str, Any]:
        res={'is_valid': False, 'message':'', 'normalized_email': None}
        if not email: res['message']='Email is required'; return res
        email=email.strip().lower()
        pat=r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
        if not re.fullmatch(pat, email): res['message']='Invalid email format'; return res
        res['is_valid']=True; res['normalized_email']=email; res['message']='OK'; return res

    @staticmethod
    def validate_phone(phone: str) -> Dict[str, Any]:
        res={'is_valid': False, 'message':'', 'formatted_phone': None}
        if not phone: res['message']='Phone number is required'; return res
        num=re.sub(r'\D','', phone)
        if len(num)==10 and num[0] in '6789':
            res['is_valid']=True; res['formatted_phone']=f"+91 {num[:5]} {num[5:]}"; res['message']='OK'
        elif len(num)==12 and num.startswith('91') and num[2] in '6789':
            m=num[2:]; res['is_valid']=True; res['formatted_phone']=f"+91 {m[:5]} {m[5:]}"; res['message']='OK'
        else:
            res['message']='Enter a valid 10-digit Indian mobile number'
        return res

    @staticmethod
    def validate_service_selection(service: str, options: list) -> Dict[str, Any]:
        res={'is_valid': False, 'message':'', 'normalized_service': None}
        if not service: res['message']=f"Choose one: {', '.join(options)}"; return res
        s=service.strip().lower()
        if s in options: res['is_valid']=True; res['normalized_service']=s; res['message']='OK'; return res
        res['message']=f"Invalid service. Choose one: {', '.join(options)}"; return res
