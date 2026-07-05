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
PRESSURE_LEVELS = ["1000hPa", "925hPa", "850hPa", "700hPa", "500hPa", "300hPa", "250hPa", "100hPa", "50hPa", "10hPa"] #config.get('PARSING', 'PRESSURE_LEVELS')

APIS = {
    # NASA: Solar flares and Radiation (Space Weather)
    "NASA_DONKI": config.get('URLS', 'NASA_DONKI'),
    # Space-Track: TLE Data for debris and satellites
    "SPACETRACK_AUTH": config.get('URLS', 'SPACETRACK_AUTH'),
    "SPACETRACK_QUERY": f"{config.get('URLS', 'SPACETRACK_QUERY')}{SPACETRACK_LIMIT}",
    # OpenMeteo: High altitude wind, temp and air density (Pressure levels)
    "METEO": config.get('URLS', 'METEO'),
    "AQI_TRENDS": config.get('URLS', 'AQI_TRENDS'),
    # OpenStreetMap: RevQVBoxLayout,erse geocoding (City/Country name)
    "OSM": config.get('URLS', 'OSM'),
    # OpenTopo: Surface elevation (SRTM 30m model)
    "OPENTOPO": config.get('URLS', 'OPENTOPO'),
    # WAQI: Ground air quality sensors (Chemical composition)
    "WAQI": config.get('URLS', 'WAQI'),
    # Flights
    "AVIATION_TRAFFIC": config.get('URLS', 'AVIATION_TRAFFIC'),
}

# = Keys = #
def get_nasa_key(): return os.getenv("NASA_API_KEY")
def get_waqi_key(): return os.getenv("WAQI_TOKEN")
def get_avwx_key(): return os.getenv("AVWX_TOKEN")
def get_st_login(): return os.getenv("SPACETRACK_LOGIN")
def get_st_pass(): return os.getenv("SPACETRACK_PASSW")

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
    except Exception as e: log(f"[ERROR] Settings JSON Update: {e}")

def log(data):
    timestamp = dt.now().strftime("%d.%m.%Y-%H:%M:%S:%f")[:-3]
    with open(LOGS_FILE_DIR, 'a', encoding="utf-8") as f: f.write(f"{timestamp} | {data}\n")
    print(data)