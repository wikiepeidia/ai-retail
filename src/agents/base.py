from abc import ABC
from src.core.engine import ModelEngine

class BaseAgent(ABC):
    def __init__(self, engine: ModelEngine, role: str):
        self.engine = engine
        self.role = role

    def generate(self, prompt: str, **kwargs):
        asset = self.engine.load_model(self.role)
        model, tokenizer = asset['model'], asset['tokenizer']
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        gen_kwargs = self.engine.config.generation.copy()
        gen_kwargs.update(kwargs)
        outputs = model.generate(**inputs, pad_token_id=tokenizer.eos_token_id, **gen_kwargs)
        return tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()