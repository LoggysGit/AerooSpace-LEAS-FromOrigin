import os
import json
from huggingface_hub import hf_hub_download

def get_model():
    repo_id = "bartowski/Qwen2.5-7B-Instruct-GGUF"
    filename = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    local_dir = os.path.join("assets", "model")
    local_path = os.path.join(local_dir, filename)

    if os.path.exists(local_path):
        update_settings(True)
        return local_path

    print("\n" + "="*50)
    print("MODEL NOT FOUND. DOWNLOADING")
    print("The application will open later. DO NOT CLOSE IT.")
    print("="*50 + "\n")

    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            local_dir_use_symlinks=False
        )
        print("\nSUCCESS: Model installed.")
        update_settings(True)
        return path
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        update_settings(False)
        return None
    
def update_settings(status):
    settings_path = os.path.join("resources", "settings.json")
    try:
        data = {}
        if os.path.exists(settings_path): 
            with open(settings_path, 'r') as f: data = json.load(f)
        data["model"] = status
        with open(settings_path, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e: print(f"[ERROR] Settings JSON Update: {e}")