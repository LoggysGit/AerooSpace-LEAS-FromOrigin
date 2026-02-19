import asyncio
import json
from datetime import datetime

import controller as model  # AI Model Controller
import parser as fetcher # Data Parser

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
    # Get Full Prompt
    full_prompt = data_fetcher.getEstimatingPrompt()
    return full_prompt

def getComparsionPrompt(inputs, data, analytics):
    return ""

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

async def analyseAllPoints(inputs):
    with open(PROMPTS_JSON_PATH, 'r', encoding='utf-8') as f: prompts = json.load(f)
    ai.setRole(prompts["role"])

    fetched, analytics = [], []
    for input in inputs:
        print(" ========== STARTING POINT ANALYSIS... ========== ")
        prompt = await getPrompt(input["spaceport"], input["coordinates"][0], input["coordinates"][1], input["target_timestamp"], input["timezone"])
        fetched.append(data_fetcher.getFetchedData())
        review = await ai.analyze(prompt)
        analytics.append(review)

    if len(inputs) > 1:
        comp_prompt = getComparsionPrompt(inputs, fetched, analytics)

    print(fetched)
    print("\n ------------------------- ANALYTICS --------------------------- \n")
    print(analytics)
    print("\n ---------------------------------------------------------------------------- \n")

    print(datetime.now())
    for item in analytics:
        clean_text = item.replace("```json", "").replace("```", "").strip()
        print(clean_text)
        print("-" * 50)

def compare(prompt):
    pass

# Test
asyncio.run(analyseAllPoints(inps))