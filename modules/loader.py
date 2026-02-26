import os
import sys
import json
from huggingface_hub import hf_hub_download

def get_path(relative_path):
    if getattr(sys, 'frozen', False): base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(current_dir) == 'modules': base_path = os.path.dirname(current_dir)
        else: base_path = current_dir
    return os.path.normpath(os.path.join(base_path, relative_path))

def get_model():
    repo_id = "bartowski/Qwen2.5-7B-Instruct-GGUF"
    filename = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    
    local_dir = get_path(os.path.join("assets", "model"))
    local_path = os.path.join(local_dir, filename)

    if os.path.exists(local_path):
        update_settings(True)
        return local_path

    print("\n" + "="*50)
    print(f"MODEL NOT FOUND IN {local_path}. DOWNLOADING FROM HUGGING FACE...")
    print("This may take a while. Please wait.")
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
        print(f"\nFATAL ERROR during download: {e}")
        update_settings(False)
        return None

def update_settings(status):
    settings_path = get_path(os.path.join("resources", "settings.json"))
    try:
        data = {}
        if os.path.exists(settings_path): 
            with open(settings_path, 'r') as f: data = json.load(f)
        data["model"] = status
        with open(settings_path, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e: 
        print(f"[ERROR] Settings JSON Update: {e}")