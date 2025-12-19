Project A: Intelligent Retail Automation Agent (Level 3)
Project A is an autonomous, on-premise AI agent designed for the Vietnamese Retail Industry. Unlike standard chatbots, it functions as a Digital Employee capable of:
Consulting: Providing business advice using context-aware memory and RAG.
Managing: Interfacing with SaaS data (Sales, Inventory, CRM).
Building: Autonomous generation of technical automation workflows (Make.com/Native JSON) based on natural language requests.
Built to run efficiently on a single L4 GPU (24GB VRAM) using a Unified 8-bit Model Architecture.
🏗️ Architecture Overview
The system utilizes a Single-Model, Multi-Persona architecture. Instead of loading multiple models, we use one high-performance model (Qwen-2.5-Coder-14B-Instruct) and dynamically swap system prompts to alter its behavior (Manager, Coder, Researcher).
System Logic Flow (Visualization)
code
Mermaid
graph TD
    User[User Input] --> Main[Main Orchestrator (main.py)]
    
    subgraph Context_Layer
        Mem[(SQLite Memory)]
        SaaS[SaaS API Mock]
        Tools[Retail Tools]
    end
    
    Main -->|Fetch History & Profile| Mem
    Main -->|Health Check| Tools
    Main -->|Send Context| Manager
    
    subgraph The_Brain_Qwen_14B
        Manager{Manager Agent}
        Coder[Coder Agent]
        Researcher[Researcher Agent]
    end
    
    Manager -->|Analyze Intent| Router{Router Decision}
    
    %% Branch 1: General Business
    Router -->|Intent: GENERAL / DATA| SaaS
    SaaS -->|Return Sales/Stock| Manager
    Manager -->|Consult & Advise| Output[Final Response]
    
    %% Branch 2: Marketing
    Router -->|Intent: MARKETING| Manager
    Manager -->|Write Copy| Output
    
    %% Branch 3: Technical Automation
    Router -->|Intent: TECHNICAL| Coder
    Coder -->|Generate JSON Blueprint| Validator[Syntax Check]
    Validator -->|Valid JSON| Integrations[Integration Manager]
    Integrations -->|Save to DB| Workflows[(Workflows Table)]
    Workflows --> Output
📂 File Structure & Components
The project is contained entirely within the src/ directory for portability.
code
Text
ProjectA/
├── main.py                  # Entry point. Handles the Event Loop, Login, and UI output.
├── requirements.txt         # Python dependencies.
├── src/
│   ├── data/                # Storage
│   │   ├── project_a.db     # SQLite DB (Chat History, Users, Stores, Sales, Workflows).
│   │   ├── docs/            # RAG Documents (PDF/TXT) for knowledge base.
│   │   └── blueprints/      # JSON Reference samples for the Coder to learn from.
│   │
│   ├── core/                # The Nervous System
│   │   ├── config.py        # Settings (Model ID, Paths, Quantization Params).
│   │   ├── engine.py        # Model Loader. Enforces Singleton pattern (loads Qwen once).
│   │   ├── memory.py        # Database Manager. Handles Context injection & History.
│   │   ├── context.py       # Login Logic. Handles Multi-store ambiguity resolution.
│   │   ├── saas_api.py      # Mock API simulating KiotViet/Sapo (Sales, Inventory).
│   │   ├── tools.py         # Deterministic Utilities (Math, Lunar Calendar, Health Check).
│   │   ├── integrations.py  # Deployment Handler (Saves JSON to DB / Mock Social Post).
│   │   └── prompts.py       # Prompt Library. Contains Persona definitions & Few-Shot examples.
│   │
│   └── agents/              # The Personas (All powered by Qwen-14B)
│       ├── base.py          # Abstract wrapper for LLM inference.
│       ├── manager.py       # THE BRAIN. Routes tasks, handles chat, intent classification.
│       ├── coder.py         # THE BUILDER. Generates strict JSON automation blueprints.
│       └── researcher.py    # THE EYES. Performs web searches (DuckDuckGo).
🧩 Detailed Component Roles
1. The Core Engines
engine.py: Loads Qwen-2.5-Coder-14B-Instruct in 8-bit quantization. This fits the model into ~16GB VRAM, leaving ~8GB buffer for long context windows (Chat History + RAG).
memory.py: Not just a logger. It actively seeds "Mock Data" (Sales, Users) so the system feels alive immediately. It formats the last 
N
N
 turns of conversation for the Manager to ensure continuity.
saas_api.py: Acts as the bridge to your business data. Currently returns mock data, but designed to be replaced with requests.get() to your real Backend API.
2. The Agents
Manager (manager.py):
Smart Routing: Distinguishes between "I want to automate" (Vague -> Ask Question) vs "Automate email on new order" (Specific -> Call Coder).
Contextual Glue: Injects Store Name, Industry, and Time into the system prompt so answers are always relevant.
Coder (coder.py):
Registry Aware: Uses a library of "Golden Templates" (in prompts.py or JSON) to ensure generated Make.com blueprints use the correct internal IDs and parameter names.
Researcher (researcher.py):
Summarizes web search results into Vietnamese business insights.
3. The Deployment Layer
integrations.py:
Instead of just printing code, it saves the generated Workflow JSON into the workflows table in SQLite.
Simulates the "Save & Activate" flow of a real SaaS platform.
🚀 Deployment Instructions
1. Hardware Requirements
GPU: NVIDIA GPU with 24GB VRAM minimum (Recommended: L4, A10g, RTX 3090/4090).
RAM: 16GB System RAM.
Disk: 50GB free space (Model weights are large).
2. Environment Setup
It is recommended to use conda or a virtual environment.
code
Bash
# 1. Create Environment
conda create -n project_a python=3.10
conda activate project_a

# 2. Install Dependencies
pip install -r requirements.txt
requirements.txt content:
code
Text
torch
transformers
accelerate
bitsandbytes
duckduckgo-search
sentence-transformers
sqlite3
lunardate
protobuf
3. Running the Agent
The project is self-contained. The first run will automatically:
Download the Qwen-14B model (approx. 9-10GB).
Initialize the SQLite Database.
Seed mock data (User: Nguyen Van A).
code
Bash
python src/main.py
🧪 Testing the Capabilities
Once the system shows ✅ Ready, try these scenarios:
Scenario A: Business Intelligence (Data + Context)
Input: "Hôm nay doanh thu thế nào?" (How is revenue today?)
Logic: Manager detects DATA_INTERNAL -> Calls saas_api.get_sales_report -> Formats response.
Output: "Doanh thu hôm nay của BabyWorld là 3.700.000 VND..."
Scenario B: Contextual Advice (Lunar Tool + Profile)
Input: "Hôm nay là ngày bao nhiêu âm? Có nên khuyến mãi không?"
Logic: Manager calls RetailTools.get_lunar_date -> Checks Profile (Baby Store) -> Suggests advice.
Output: "Hôm nay là 15 Âm lịch... Nên chạy chương trình nhẹ nhàng..."
Scenario C: Automation Building (The "Meta-Agent")
Input: "Tự động gửi email cảm ơn khi có đơn hàng mới."
Logic: Manager detects TECHNICAL (Specific) -> Coder generates JSON -> Integrations saves to DB.
Output: "Đã thiết kế xong. Workflow ID: 5. ✅ ĐÃ LƯU THÀNH CÔNG."
🔮 Future Roadmap (Beyond Phase 22)
Real API Hookup: Replace saas_api.py methods with real SQL queries to your Postgres/MySQL production DB.
Frontend Integration: Connect this Python backend to your Website via FastAPI.
User types in Web Chat -> FastAPI sends to main.py -> Agent Returns Text/JSON.
Vision Support: Upgrade to Qwen-VL to allow users to upload photos of invoices or products for auto-entry.# ai-retail
