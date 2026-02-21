import asyncio
import json
from datetime import datetime

import modules.controller as model  # AI Model Controller
import modules.parser as fetcher # Data Parser

# === Constants ===
MODEL_PATH = "assets/model/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
PROMPTS_JSON_PATH = "resources/prompts.json"

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
    print(json.dumps(clear_ans, indent=4, ensure_ascii=False))
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
        comparsion = ""#ai.analyze(comp_prompt)
        print(" ========== COMPARSION VERDICT SUCCESSFUL! ========== ")

    #print(datetime.now())

    file = f"""
{points},
{fetched},
{predicted},
{analytics},
{comparsion}
"""
    print(file)
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"report_{timestamp}.json"
        with open(file_name, "w", encoding="utf-8") as f: json.dump(file, f, ensure_ascii=False, indent=4)
        print(f"[A]: Data successfully saved to {file_name}")
        return file_name
    except Exception as e:
        print(f"[A]: Failed to save file: {e}")
        return None

# Test
#asyncio.run(analyseAllPoints(inps))