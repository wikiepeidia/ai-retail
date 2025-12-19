import sys
import os
import torch
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.insert(0, project_root)

# Import Core Systems
from src.core.engine import ModelEngine
from src.core.memory import MemoryManager
from src.core.context import ContextResolver
from src.core.saas_api import SaasAPI
from src.core.integrations import IntegrationManager
from src.agents.manager import ManagerAgent
from src.agents.coder import CoderAgent
from src.agents.researcher import ResearcherAgent
from src.agents.vision import VisionAgent

# --- INITIALIZATION (Load Models Once) ---
print("🚀 Starting Project A Server...")
try:
    engine = ModelEngine() # Loads Qwen-14B (Heavy)
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    engine = None

memory = MemoryManager()
resolver = ContextResolver(memory)
saas = SaasAPI()
integrations = IntegrationManager(memory)

# Initialize Agents
manager = ManagerAgent(engine, memory)
coder = CoderAgent(engine, memory)
researcher = ResearcherAgent(engine)

# Vision is OFF by default to avoid slow/fragile loads. Opt-in with ENABLE_VISION=1.
ENABLE_VISION = os.environ.get("ENABLE_VISION", "0") in ["1", "true", "True"]
if not ENABLE_VISION:
    print("⚠️ Vision disabled by default (set ENABLE_VISION=1 to load Florence)")
    vision = None
    vision_enabled = False
else:
    try:
        # Vision model is heavy; make it optional
        vision = VisionAgent()
        vision_enabled = True
    except Exception as e:
        print(f"⚠️ Vision init failed, disabling vision: {e}")
        vision = None
        vision_enabled = False

# Shared key to protect /plan endpoint (set AI_SHARED_KEY env in Colab)
AI_SHARED_KEY = os.environ.get("AI_SHARED_KEY", "")

app = FastAPI(title="Project A API", version="1.0.0")


@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Project A API",
        "endpoints": ["/health", "/chat", "/plan", "/upload_image"],
        "vision_enabled": vision_enabled,
    }

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    user_id: int
    message: str
    store_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None
    data: Optional[dict] = None

class PlanRequest(BaseModel):
    prompt: str
    context: Optional[dict] = None

class PlanResponse(BaseModel):
    nodes: list
    edges: list
    notes: Optional[str] = None

# --- ENDPOINTS ---

@app.get("/health")
def health_check():
    return {"status": "online", "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}


@app.post("/plan", response_model=PlanResponse)
async def plan_endpoint(req: PlanRequest, x_ai_key: Optional[str] = Header(default=None)):
    """Generate a simple workflow plan from natural language.

    Security: requires header X-AI-Key matching AI_SHARED_KEY env.
    """
    if AI_SHARED_KEY and x_ai_key != AI_SHARED_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")

    # Minimal deterministic demo plan; swap in agent logic as needed
    nodes = [
        {"id": "n1", "type": "google_sheet_read", "config": {"sheetId": "SHEET_ID", "range": "A1:C10"}},
        {"id": "n2", "type": "google_doc_write", "config": {"docId": "DOC_ID", "template": "Summary: {{n1.data}}"}},
    ]
    edges = [{"from": "n1", "to": "n2"}]
    notes = "demo plan from prompt: " + prompt

    return {"nodes": nodes, "edges": edges, "notes": notes}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Main conversation endpoint.
    """
    print(f"📩 Request from User {req.user_id}: {req.message}")
    
    # 1. Context Setup
    # In a real app, you might validate the token here
    if req.store_id:
        # Fetch store details directly
        # For prototype, we simulate the resolver logic manually or assume store_id is valid
        # Let's simple set db context for now
        manager.db_context = f"Store ID: {req.store_id} (Context Loaded)"
    
    # 2. History
    memory.add_message("user", req.message)
    history_str = memory.get_context_string(limit=6)

    # 3. Analyze
    decision = manager.decide_tool(req.message, history_str)
    tool_name = decision.get("tool")
    args = decision.get("args", {})
    
    response_text = ""
    action_type = "chat"
    meta_data = {}

    # 4. Execute Logic (Simplified from main.py)
    if tool_name == "technical_planner":
        action_type = "automation_design"
        plan = manager.plan(req.message)
        code = coder.write_code(req.message, plan)
        
        # Save internally
        # Extract JSON (simplified)
        import re
        match = re.search(r"```json\n(.*?)\n```", code, re.DOTALL)
        if match:
            json_payload = match.group(1)
            # Save to DB
            if req.store_id:
                res = integrations.deploy_internal(req.store_id, json_payload, "API Generated Flow")
                meta_data = res
        
        response_text = f"Đã thiết kế xong quy trình.\n\n{code}"

    elif tool_name:
        action_type = "tool_use"
        # Handle Sales/Inventory logic here...
        # (For brevity, I'll map just one example)
        if tool_name == "get_sales_report":
            val = saas.get_sales_report(req.store_id or 1, "today")
            context = f"SALES: {val}"
            response_text = manager.consult(req.message, context, history_str)
        else:
            # Fallback tool usage
            response_text = manager.consult(req.message, f"Tool {tool_name} triggered", history_str)

    else:
        # General Chat
        response_text = manager.consult(req.message, "", history_str)

    # 5. Save & Return
    # Clean output
    response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
    memory.add_message("assistant", response_text)
    
    return {
        "response": response_text,
        "action_taken": action_type,
        "data": meta_data
    }

@app.post("/upload_image")
async def upload_image(user_id: int, file: UploadFile = File(...)):
    """
    Endpoint to handle image uploads for Vision analysis.
    If vision model failed to load, return a clear error.
    """
    if not vision_enabled or vision is None:
        raise HTTPException(status_code=503, detail="Vision model not available")

    file_location = f"src/data/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    # Run Vision
    result = vision.analyze_image(file_location)
    
    return {"filename": file.filename, "analysis": result}


# --- LOCAL/NOTEBOOK ENTRYPOINT ---
def maybe_start_ngrok(port: int):
    """Optionally start an ngrok tunnel when AUTO_NGROK=1 and pyngrok is available."""
    auto = os.environ.get("AUTO_NGROK", "0") in ["1", "true", "True"]
    if not auto:
        return None

    try:
        from pyngrok import ngrok
    except ImportError:
        print("⚠️ AUTO_NGROK requested but pyngrok is not installed. Run: pip install pyngrok")
        return None

    token = os.environ.get("NGROK_AUTHTOKEN")
    if token:
        ngrok.set_auth_token(token)

    tunnel = ngrok.connect(port, bind_tls=True)
    print(f"🌐 ngrok tunnel started: {tunnel.public_url}")
    return tunnel.public_url


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    maybe_start_ngrok(port)

    import uvicorn
    # Pass app object directly to avoid a second import that re-triggers model loading
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)