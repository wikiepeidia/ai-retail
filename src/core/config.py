import torch
import os

class Config:
    def __init__(self):
        # Resolve paths relative to THIS file (src/core/config.py) -> Go up 2 levels to Root
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Data now lives inside SRC for portability
        self.SRC_DATA_DIR = os.path.join(self.PROJECT_ROOT, 'src', 'data')
        self.DB_PATH = os.path.join(self.SRC_DATA_DIR, 'project_a.db')
        
        # RAG Docs remain in root data for easy upload, or move to src if preferred
        self.DOCS_DIR = os.path.join(self.PROJECT_ROOT, 'data', 'docs') 
        
        os.makedirs(self.SRC_DATA_DIR, exist_ok=True)
        os.makedirs(self.DOCS_DIR, exist_ok=True)
        
        self.SYSTEM_CONTEXT = "You are Project A, a Retail Assistant."

        MODEL_ID = "Qwen/Qwen2.5-Coder-14B-Instruct"

        self.models = {
            "manager": MODEL_ID,
            "coder": MODEL_ID,
            "researcher": MODEL_ID
        }
        
        self.quantization = {
            "load_in_8bit": True,
        }
        
        # OPTIMIZATION: Utilization of extra VRAM
        # We increase max_new_tokens to allow for MASSIVE blueprints.
        self.generation = {
            "max_new_tokens": 4096, # Doubled from 2048
            "temperature": 0.2,
            "do_sample": True
        }