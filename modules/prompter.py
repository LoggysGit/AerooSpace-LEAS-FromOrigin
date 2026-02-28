import copy
import os
import re
import sys
import json
import random
from datetime import datetime

import modules.controller as model  # AI Model Controller
import modules.parser as fetcher # Data Parser

def get_path(relative_path):
    if getattr(sys, 'frozen', False): base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(current_dir) == 'modules': base_path = os.path.dirname(current_dir)
        else: base_path = current_dir
    return os.path.normpath(os.path.join(base_path, relative_path))

# === Constants ===
MODEL_PATH = get_path(os.path.join("assets", "model", "Qwen2.5-7B-Instruct-Q4_K_M.gguf"))
PROMPTS_JSON_PATH = get_path(os.path.join("resources", "prompts.json"))
REPORTS_DIR = get_path(os.path.join("resources", "reports"))
if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR, exist_ok=True)

# === Objects & Variables ===
ai = model.AIModel(MODEL_PATH)

data_fetcher = fetcher.DataControlManager()

async def getPrompt(spaceport, lat, lon, datetime, timezone):
    # Set
    data_fetcher.setInput(spaceport, lat, lon, datetime, timezone)
    # Fetch
    await data_fetcher.fetchAllData()
    # Predict
    print(" ========== STARTING PREDICTION... ========== ")
    pr_prompt = data_fetcher.getPredictionPrompt()
    raw_ans = await ai.analyze(pr_prompt)
    clear_ans = raw_ans.replace("```json", "").replace("```", "").strip()
    print(" ========== PREDICTION COMPLETE! DATA: ========== ") #
    print(clear_ans) #
    data_fetcher.updatePredicted(clear_ans)
    print("==================================================")
    # Get Full Prompt
    full_prompt = data_fetcher.getEstimatingPrompt()
    return clear_ans, full_prompt

def getComparsionPrompt(input, data, analytics):
    return f"""
Your task is to conduct a rigorous comparative analysis between multiple launch sites.

INPUT PARAMETERS (User Requirements):
{input}

RAW DATA FOR POINTS (Meteorology, Geodesy, Space Weather):
{data}

SCORING ANALYTICS (S1-S5 Indices):
{analytics}

STRICT INSTRUCTIONS:
1. "best": Return the integer index of the top-performing location.
2. "comparing": Create a concise technical comparison. Focus on WHY the scores differ. Mention specific "Red Lines" or critical advantages (e.g., "Site A has 15% better fuel efficiency due to latitude, but Site B has safer wind profiles").
3. "final_verdict": A definitive professional conclusion. Why is the winner the safest and most efficient choice for THIS specific mission?
4. "recommendations": Provide 2-3 actionable steps (e.g., "Delay launch by 2 hours to avoid peak solar activity" or "Recalibrate stabilizers for S2 wind shear").

OUTPUT FORMAT:
Return ONLY a valid JSON object. No prose before or after.
{{
    "comparing": "str",
    "final_verdict": "str",
    "best": str, // Location (STRICTLY ACCORDING TO GIVEN DATA)
    "recommendations": "str"
}}
"""

async def analyseAllPoints(points):
    with open(PROMPTS_JSON_PATH, 'r', encoding='utf-8') as f: prompts = json.load(f)
    ai.setRole(prompts["role"])

    fetched, predicted, analytics = [], [], []
    for input in points:
        print(" = POINT ANALYSIS STARTED... = ")
        try:
            pr, prompt = await getPrompt(input["spaceport"], input["coordinates"][0], input["coordinates"][1], input["target_timestamp"], input["timezone"])

            fetched_data = data_fetcher.getFetchedData()
            fetched.append(copy.deepcopy(fetched_data))

            predicted.append(pr)

            review = await ai.analyze(prompt)
            analytics.append(review)
            print(" = POINT ANALYZED SUCCESSFULLY! = ")
        except Exception as e: print(f" = ANALYZING ERROR: {e} = ")

    comparsion = ""
    if len(points) > 1:
        print(" = COMPARING... = ")
        comp_prompt = getComparsionPrompt(points, fetched, analytics)
        comparsion = await ai.analyze(comp_prompt)
        print(" = COMPARSION VERDICT SUCCESSFUL! = ")
    
    dir = ""
    if points != []: dir = save_report(points, fetched, predicted, analytics, comparsion)
    
    return dir

def clean_json_string(text):
    if not isinstance(text, str): return text
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    return match.group(0) if match else text
def ensure_obj(data):
    if data is None: return []

    if isinstance(data, list): return [ensure_obj(item)[0] if ensure_obj(item) else {} for item in data]
    if isinstance(data, str):
        cleaned = clean_json_string(data)
        try: 
            print(f"[A]: Trying to parse: {data}")
            parsed = json.loads(cleaned)
            return [parsed] if isinstance(parsed, dict) else parsed
        except Exception as e:
            print(f"[A] JSON Parse Error: {e}")
            return []   
    if isinstance(data, dict): return [data]

    return []
def save_report(points, fetched, predicted, analytics, comparsion):
    print("[A] Saving data...")
    if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
    try:
        file_data = {
            "point_count": len(points),
            "points": points,
            "fetched": fetched,
            "predicted": list(ensure_obj(predicted)),
            "analytics": ensure_obj(analytics),
            "comparison": ensure_obj(comparsion)
        }

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"report_{timestamp}_{random.randint(1, 9999)}.json"

        full_path = os.path.join(REPORTS_DIR, file_name)
        with open(full_path, "w", encoding="utf-8") as f: json.dump(file_data, f, ensure_ascii=False, indent=4)
            
        print(f"[A]: Data successfully saved to {file_name}")
        return file_name
    except Exception as e:
        print(f"[A]: Failed to save file: {e}")
        return "null"