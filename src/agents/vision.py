from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch
import os
import logging

class VisionAgent:
    def __init__(self):
        print("👁️ [Vision] Initializing Florence-2 (The Eye)...")
        self.model_id = 'microsoft/Florence-2-large'
        # Check GPU availability
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Use float16 for GPU to save memory, float32 for CPU
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                trust_remote_code=True,
                torch_dtype=self.dtype
            ).to(self.device)
            
            self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
            print("✅ Vision Agent Loaded.")
        except Exception as e:
            print(f"❌ Vision Load Failed: {e}")
            self.model = None

    def analyze_image(self, image_path, task_hint="OCR"):
        """
        Analyzes an image based on the context.
        - If task_hint implies 'marketing' or 'describe', use CAPTION.
        - Otherwise, default to OCR (Read text).
        """
        if not self.model:
            return "Vision model not loaded."

        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"

        try:
            image = Image.open(image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
        except Exception as e:
            return f"Error opening image: {e}"

        # 1. Determine Prompt based on intent
        task_prompt = "<OCR>"
        if any(x in task_hint.lower() for x in ["marketing", "bài viết", "miêu tả", "quảng cáo", "describe", "caption"]):
            task_prompt = "<DETAILED_CAPTION>"
        
        # 2. Prepare Inputs
        inputs = self.processor(text=task_prompt, images=image, return_tensors="pt").to(self.device, self.dtype)

        # 3. Generate
        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            do_sample=False,
            num_beams=3
        )

        # 4. Decode
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        
        # 5. Post-Process
        parsed_answer = self.processor.post_process_generation(
            generated_text, 
            task=task_prompt, 
            image_size=(image.width, image.height)
        )
        
        # Return clean string result
        result = parsed_answer.get(task_prompt, "")
        
        # FIXED: Use concatenation to avoid f-string syntax errors on write
        header = "[IMAGE ANALYSIS - Mode: " + task_prompt + "]"
        return header + "\n" + str(result)