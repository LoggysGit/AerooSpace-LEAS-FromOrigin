import os
import sys

import json
from datetime import datetime as dt

import configparser

# = Directories = #
def get_path(relative_path):
    if getattr(sys, 'frozen', False):
        external_targets = [".env", "reports"]
        is_external = any(relative_path.startswith(target) for target in external_targets)
        
        if is_external: base_path = os.path.dirname(sys.executable)
        else: base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir) if os.path.basename(current_dir) == 'modules' else current_dir 
    return os.path.normpath(os.path.join(base_path, relative_path))

STYLES = get_path(os.path.join("assets", "styles.qss"))
REPORTS_PATH = get_path("reports")
ENVIRONMENT_PATH = get_path(".env")

SETTINGS_PATH = get_path(os.path.join("resources", "settings.json"))

PROMPTS_JSON_PATH = get_path(os.path.join("resources", "prompts.json"))
REPORTS_DIR = get_path("reports")

LOGS_FILE_DIR = get_path("logs.log")

with open(STYLES, "r", encoding="utf-8") as f: STYLESHEET = f.read()

# = Config = #
config = configparser.ConfigParser()
config.read(get_path("config.cfg"))

LLM_NAME = config.get('GENERAL', 'LLM_MODEL')
LLM_REPO_ID = config.get('GENERAL', 'LLM_REPO')

HISTORY_WINDOW_YEARS = config.get('PARSING', 'HISTORY_WINDOW_YEARS')
SPACETRACK_LIMIT = config.get('PARSING', 'SPACETRACK_LIMIT')

# = Paths = #
MODEL_PATH = get_path(os.path.join("assets", "model", LLM_NAME))

if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR, exist_ok=True)

# = Functions = #
def update_settings(status):
    try:
        data = {}
        if os.path.exists(SETTINGS_PATH): 
            with open(SETTINGS_PATH, 'r') as f: data = json.load(f)
        data["model"] = status
        with open(SETTINGS_PATH, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e: 
        print(f"[ERROR] Settings JSON Update: {e}")

def log(data):
    timestamp = dt.now().strftime("%d.%m.%Y-%H:%M:%S:%f")[:-3]
    with open(LOGS_FILE_DIR, 'a', encoding="utf-8") as f: f.write(f"{timestamp} | {data}\n")
    print(data)