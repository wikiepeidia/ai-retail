import json
import re
from datetime import datetime
import pytz
from src.agents.base import BaseAgent
from src.core.prompts import Prompts

class ManagerAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, "manager")
        self.memory = memory
        self.db_context = "" 

    def set_db_context(self, context_str):
        self.db_context = context_str

    def get_dynamic_context(self):
        return f"{Prompts.SYSTEM_CONTEXT}\n\n[DATA]\n{self.db_context}"

    def _extract_json(self, text):
        try:
            match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
            if match: return json.loads(match.group(1))
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match: return json.loads(match.group(0))
        except: pass
        return None

    def analyze_task(self, task: str, history_str: str = ""):
        task_lower = task.lower().strip()
        
        # --- 1. MARKETING INTENT ---
        if any(x in task_lower for x in ["viết bài", "quảng cáo", "facebook", "content", "stt", "đăng bài"]):
            return {"category": "MARKETING"}

        # --- 2. TECHNICAL INTENT (With Vague Check) ---
        # Triggers: "build", "automation", "make.com"
        tech_keywords = ["tạo", "build", "automation", "make.com", "tự động hóa", "kết nối", "workflow"]
        
        has_tech_keyword = any(x in task_lower for x in tech_keywords)
        
        # CRITICAL FIX: Check if the request is specific enough
        # If it's short (< 30 chars) AND lacks specific nouns (email, sheet, order, zalo), treat as GENERAL conversation.
        specific_nouns = ["email", "mail", "sheet", "exel", "đơn", "khách", "kho", "zalo", "facebook", "nhắn", "gửi"]
        is_specific = any(n in task_lower for n in specific_nouns)
        
        # Exception: If history has context (e.g., "Option 2"), it is specific even if short.
        has_history_context = "option" in task_lower or "cái số" in task_lower or "cái đó" in task_lower

        if has_tech_keyword:
            if is_specific or has_history_context or len(task_lower) > 50:
                return {"category": "TECHNICAL"}
            else:
                # User said "I want automation" but didn't say WHAT.
                # Route to GENERAL so Consultant can ask.
                return {"category": "GENERAL"}
        
        # --- 3. DATA INTENT ---
        data_keywords = ["doanh thu", "tồn kho", "bán được", "bao nhiêu", "thống kê"]
        if any(k in task_lower for k in data_keywords):
            return {"category": "DATA_INTERNAL", "db_metric": "revenue_today"}

        # --- 4. GENERAL (Default) ---
        return {"category": "GENERAL"}

    def consult(self, task: str, context_data: str = "", history_str: str = ""):
        sys_prompt = self.get_dynamic_context()
        
        prompt = f'''<|im_start|>system
{sys_prompt}

CHAT HISTORY:
{history_str}

DATA: {context_data}

INSTRUCTION: Answer helpfuly in Vietnamese.
- If the user asks vaguely about "Automation" (e.g. "I want to automate"), DO NOT generate code. Instead, ask them SPECIFIC questions: "Bạn muốn tự động hóa quy trình nào? (Ví dụ: Chốt đơn, CSKH, hay Quản lý kho?)".
- Be professional and friendly.
<|im_end|>
<|im_start|>user
{task}
<|im_end|>
<|im_start|>assistant
'''
        return self.generate(prompt, max_new_tokens=1024)

    def write_marketing(self, task: str):
        return self.generate(f"<|im_start|>system\nCopywriter.\n<|im_end|>\n<|im_start|>user\n{task}<|im_end|>\n<|im_start|>assistant\n", max_new_tokens=1024)

    def plan(self, task: str, history_str: str = ""):
        sys_prompt = self.get_dynamic_context()
        prompt = f'''<|im_start|>system
{sys_prompt}
TASK: Architect an Automation Workflow.
CONTEXT FROM HISTORY: {history_str}
USER REQUEST: {task}
<|im_end|>
<|im_start|>assistant
'''
        return self.generate(prompt, max_new_tokens=1500)
    
    def review(self, task: str, code: str):
        prompt = f'''<|im_start|>system
Reviewer. Analyze this JSON.
<|im_end|>
<|im_start|>user
{code}
<|im_end|>
<|im_start|>assistant
'''
        return self.generate(prompt, max_new_tokens=512)