import sys
import os
import time
import torch
import re
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.insert(0, project_root)

from src.core.engine import ModelEngine
from src.core.memory import MemoryManager
from src.core.context import ContextResolver
from src.core.saas_api import SaasAPI
from src.core.tools import RetailTools
from src.core.integrations import IntegrationManager
from src.agents.manager import ManagerAgent
from src.agents.coder import CoderAgent
from src.agents.researcher import ResearcherAgent
from src.agents.vision import VisionAgent

def clean_output(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.replace("</think>", "").replace("<think>", "").strip()

def extract_json_block(text):
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def extract_image_path(text):
    match = re.search(r"(\S+\.(jpg|jpeg|png|bmp|webp))", text, re.IGNORECASE)
    if match: return match.group(1)
    return None

def main():
    print("--- ProjectA: Phase 24 (Visible Storage) ---")
    
    try: engine = ModelEngine()
    except: pass 

    memory = MemoryManager()
    resolver = ContextResolver(memory)
    saas = SaasAPI()
    integrations = IntegrationManager(memory)
    
    manager = ManagerAgent(engine, memory)
    coder = CoderAgent(engine, memory)
    researcher = ResearcherAgent(engine)
    vision = VisionAgent()

    # LOGIN
    CURRENT_USER_ID = 1 
    status, data = resolver.resolve_login(CURRENT_USER_ID)
    if status == "AMBIGUOUS":
        print("\n🏪 Vui lòng chọn cửa hàng:")
        for i, s in enumerate(data): print(f"[{i+1}] {s['name']}")
        try:
            choice = int(input("Số: ")) - 1
            manager.set_db_context(resolver.set_active_store(data[choice]))
        except: pass
    elif status == "READY":
        manager.set_db_context(data)

    print("\n✅ Ready.")

    while True:
        try:
            user_input = input("\n💬 Bạn: ").strip()
            if user_input.lower() in ['exit', 'quit']: break
            if not user_input: continue

            # --- 0. VISION CHECK ---
            image_path = extract_image_path(user_input)
            vision_context = ""
            if image_path:
                print(f"👁️ Detected Image: {image_path}")
                if os.path.exists(image_path):
                    print("    [Vision] Analyzing...")
                    vision_result = vision.analyze_image(image_path, task_hint=user_input)
                    vision_context = f"\n[USER IMAGE DATA]:\n{vision_result}\n"
                else:
                    print(f"❌ File not found: {image_path}")

            full_context_input = user_input + vision_context

            # 1. HISTORY
            memory.add_message("user", user_input)
            history_str = memory.get_context_string(limit=6)

            # 2. ANALYZE
            meta = manager.analyze_task(full_context_input, history_str)
            category = meta.get("category", "GENERAL")
            
            if category == "TECHNICAL":
                print(f"\n🤖 Đã nhận yêu cầu. Hệ thống đang thiết kế quy trình...")
                print("    [Architect] Designing Logic...")
                plan = manager.plan(full_context_input, history_str)
                
                print("    [Builder] Configuring Nodes...")
                raw_code = coder.write_code(full_context_input, plan)
                code = clean_output(raw_code)
                
                print("\n" + "-"*40)
                print(code) 
                
                confirm = input("\n💾 Lưu quy trình này? (y/n): ")
                if confirm.lower() == 'y':
                    json_payload = extract_json_block(code)
                    store_id = resolver.active_store['id']
                    
                    # Create a readable name
                    wf_name = f"Flow_{int(time.time())}"
                    
                    res = integrations.deploy_internal(store_id, json_payload, wf_name)
                    if res['status'] == 'success':
                        print(f"✅ ĐÃ LƯU THÀNH CÔNG!")
                        print(f"📂 File saved at: {res['file_path']}")
                        print(f"👉 You can download this file from the 'my_workflows' folder.")

            elif category == "MARKETING":
                print("    [Creative] Drafting...")
                content = manager.write_marketing(full_context_input)
                print("\n" + "="*40)
                print(clean_output(content))

            elif category == "DATA_INTERNAL":
                store_id = resolver.active_store['id']
                val = saas.get_sales_report(store_id, "today")
                res = f"Revenue: {val['revenue']}"
                print("    (Đang trả lời...)")
                final = manager.consult(full_context_input, res, history_str)
                print("\n" + clean_output(final))

            else: 
                print("    (Đang suy nghĩ...)")
                final = manager.consult(full_context_input, "", history_str)
                print("\n" + clean_output(final))
            
            memory.add_message("assistant", "Response Generated")
            torch.cuda.empty_cache()

        except KeyboardInterrupt: break
        except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()