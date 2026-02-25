import os
import sys
from huggingface_hub import hf_hub_download

def get_model():
    repo_id = "bartowski/Qwen2.5-7B-Instruct-GGUF"
    filename = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    local_dir = os.path.join("assets", "model")
    local_path = os.path.join(local_dir, filename)

    if os.path.exists(local_path):
        return local_path

    print("\n" + "="*50)
    print("!!! MODEL NOT FOUND. DOWNLOADING (4.7 GB) !!!")
    print("The application will freeze. DO NOT CLOSE IT.")
    print("="*50 + "\n")

    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            local_dir_use_symlinks=False
        )
        print("\nSUCCESS: Model installed.")
        return path
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        return None