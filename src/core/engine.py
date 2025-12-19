import torch
import gc
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from src.core.config import Config

logger = logging.getLogger("System")

class ModelEngine:
    def __init__(self):
        self.config = Config()
        self.loaded_models = {}
        # Clear VRAM before loading to prevent fragmentation
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
            
        self._load_all_models()

    def _load_all_models(self):
        print("⚡ [Engine] Initializing Unified Architecture...")
        
        # 1. GROUP ROLES BY MODEL NAME
        # This ensures we only load 'Qwen-14B' ONCE, even if used by 3 agents.
        unique_models = {}
        for role, model_name in self.config.models.items():
            if model_name not in unique_models:
                unique_models[model_name] = []
            unique_models[model_name].append(role)

        # 2. LOAD EACH UNIQUE MODEL ONCE
        for model_name, roles in unique_models.items():
            role_list = ", ".join(roles).upper()
            print(f"   -> Loading Shared Model: {model_name}")
            print(f"      (Assigned to: {role_list})...")
            
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                tokenizer.padding_side = "left"
                if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token

                # 4-bit Quantization is MANDATORY for 14B on L4 GPU
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=BitsAndBytesConfig(**self.config.quantization),
                    device_map="auto",
                    trust_remote_code=True
                )
                
                # Shared Asset
                asset = {"model": model, "tokenizer": tokenizer}
                
                # Assign to all roles
                for role in roles:
                    self.loaded_models[role] = asset
                    
            except Exception as e:
                print(f"❌ Failed to load {model_name}: {e}")
                raise e
        
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            print(f"✅ VRAM Status: {(total-free)/1e9:.2f}GB / {total/1e9:.2f}GB Used.")

    def load_model(self, role: str):
        if role not in self.loaded_models:
            raise ValueError(f"Role {role} not loaded! Available: {list(self.loaded_models.keys())}")
        return self.loaded_models[role]