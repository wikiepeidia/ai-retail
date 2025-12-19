from src.agents.base import BaseAgent
from src.core.prompts import Prompts

class CoderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, "coder")

    def write_code(self, task: str, plan: str, feedback: str = ""):
        # We explicitly mention Make.com in the user prompt to trigger the right mode
        prompt = f'''{Prompts.CODER_SYSTEM}
<|im_start|>user
TASK: {task}

ARCHITECT PLAN:
{plan}

INSTRUCTIONS:
- If this is an automation, generate a Make.com Blueprint (JSON).
- Ensure the "mapper" fields use the correct ID references from previous steps.

{f"FEEDBACK FROM PREVIOUS ERROR: {feedback}" if feedback else ""}
<|im_end|>
<|im_start|>assistant
'''
        # Low temp for precision
        return self.generate(prompt, max_new_tokens=3000, temperature=0.1)