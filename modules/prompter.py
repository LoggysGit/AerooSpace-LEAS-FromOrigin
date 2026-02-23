import asyncio
import os
import re
import json
from datetime import datetime

import modules.controller as model  # AI Model Controller
import modules.parser as fetcher # Data Parser

# === Constants ===
MODEL_PATH = "assets/model/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
PROMPTS_JSON_PATH = "resources/prompts.json"
REPORTS_PATH = "resources/reports/"

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
    print("============================================================")
    # Get Full Prompt
    full_prompt = data_fetcher.getEstimatingPrompt()
    return clear_ans, full_prompt

def getComparsionPrompt(input, data, analytics):
    return f"""
YOU NEED TO COMPARE
INPUT DATA:
{input}
ALL FETCHED DATA ABOUT POINTS:
{data}
FINAL OVERVIEW:
{analytics}
GIVE ANSWER IN THIS FORMAT:
{{
    "best": 0,
    "comparing": str,
    "final_verdict": str,
    "recommendations": str
}}
"""

inps = [
    {
        "spaceport": "Hokkaido Spaceport",
        "coordinates": [42.5028, 143.4414], # Япония, северный космодром
        "target_timestamp": "2026-03-01T10:00:00Z",
        "timezone": "UTC+9",
    },
    {
        "spaceport": "Alcantara Launch Center",
        "coordinates": [-2.3731, -44.3964], # Бразилия, экватор (идеально для S3/S5)
        "target_timestamp": "2026-03-05T15:00:00Z",
        "timezone": "UTC-3",
    },
]

async def analyseAllPoints(points):
    with open(PROMPTS_JSON_PATH, 'r', encoding='utf-8') as f: prompts = json.load(f)
    ai.setRole(prompts["role"])

    fetched, predicted, analytics = [], [], []
    for input in points:
        print(" ========== POINTS ANALYSIS STARTED... ========== ")
        try:
            pr, prompt = await getPrompt(input["spaceport"], input["coordinates"][0], input["coordinates"][1], input["target_timestamp"], input["timezone"])
        
            fetched.append(data_fetcher.getFetchedData())

            predicted.append(pr)

            review = await ai.analyze(prompt)
            analytics.append(review)
            print(" ========== POINTS ANALYZED SUCCESSFULLY! ========== ")
        except Exception as e: print(f" ========== ANALYZING ERROR: {e} ========== ")

    comparsion = ""
    if len(points) > 1:
        print(" ========== COMPARING STARTED... ========== ")
        comp_prompt = getComparsionPrompt(points, fetched, analytics)
        comparsion = "-"#ai.analyze(comp_prompt)
        print(" ========== COMPARSION VERDICT SUCCESSFUL! ========== ")
    
    if points != []: save_report(points, fetched, predicted, analytics, comparsion)

    #print(datetime.now())

def clean_json_string(text):
    if not isinstance(text, str): return text
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    return match.group(0) if match else text
def ensure_obj(data):
    if data is None: return []
    
    if isinstance(data, str):
        cleaned = clean_json_string(data)
        try: data = json.loads(cleaned)
        except Exception as e:
            print(f"[A] JSON Parse Error: {e}")
            return []
    if isinstance(data, dict): return [data]
    if isinstance(data, list): return data
        
    return []
def save_report(points, fetched, predicted, analytics, comparsion):
    try:
        file_data = {
            "point_count": len(points),
            "points": points,
            "fetched": fetched,
            "predicted": list(ensure_obj(predicted)), # MAKE LIST
            "analytics": ensure_obj(analytics), # MAKE LIST
            "comparison": ensure_obj(comparsion)
        }

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"report_{timestamp}.json"
        
        # Use os.path.join to avoid double slashes or missing ones
        full_path = os.path.join(REPORTS_PATH, file_name)

        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=4)
            
        print(f"[A]: Data successfully saved to {file_name}")
        return file_name
    except Exception as e:
        print(f"[A]: Failed to save file: {e}")
        return "error.json"

# Test
#asyncio.run(analyseAllPoints(inps))