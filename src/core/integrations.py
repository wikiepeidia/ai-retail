import json
import time
import os
import re

class IntegrationManager:
    """
    Handles Internal Platform Operations.
    Saves to DB (System Memory) AND File System (User Accessibility).
    """
    def __init__(self, memory_manager):
        self.memory = memory_manager
        # Create a visible folder for users to find their files
        self.save_dir = "my_workflows"
        os.makedirs(self.save_dir, exist_ok=True)

    def _sanitize_filename(self, name):
        # Turn "Auto-Gen: Email Flow" into "Auto-Gen_Email_Flow"
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    def deploy_internal(self, store_id, blueprint_json, name="New Automation"):
        """
        1. Saves to DB.
        2. Exports to .json file.
        """
        print(f"    [Internal] Saving workflow '{name}'...")
        
        # VALIDATION
        try:
            if isinstance(blueprint_json, str):
                payload = json.loads(blueprint_json)
            else:
                payload = blueprint_json
        except:
            return {"status": "error", "message": "Invalid JSON format"}

        # 1. SAVE TO DB (System Record)
        wf_id = self.memory.save_workflow(store_id, name, payload)
        
        # 2. SAVE TO FILE (User Access)
        safe_name = self._sanitize_filename(name)
        filename = f"{self.save_dir}/WF_{wf_id}_{safe_name}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        # RETURN SUCCESS
        return {
            "status": "success",
            "workflow_id": wf_id,
            "file_path": filename,
            "message": "Workflow saved to Database and File System."
        }

    def post_to_social(self, platform, content):
        print(f"    [Network] Posting to {platform}...")
        time.sleep(1)
        return {"status": "published", "link": "http://fb.com/post/123"}