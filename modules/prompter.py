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
    data_fetcher.setInput(spaceport, lat, lon, datetime, timezone)
    await data_fetcher.fetchAllData()
    full_prompt = data_fetcher.getSinglePrompt()
    return full_prompt

def getComparsionPrompt(inputs, data, analytics):
    return ""

inps = [
    {
        "spaceport": "custom",
        "coordinates": [35.2458, 139.1023], 
        "target_timestamp": "2026-03-01T10:00:00Z",
        "timezone": "UTC+9",
    },
    {
        "spaceport": "custom",
        "coordinates": [-23.0008, -43.3547],
        "target_timestamp": "2026-03-05T15:00:00Z",
        "timezone": "UTC-3",
    },
    {
        "spaceport": "custom",
        "coordinates": [28.5721, -80.6480], 
        "target_timestamp": "2026-03-10T12:00:00Z",
        "timezone": "UTC-5",
    }
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
    print("\n ----------------------------------- A -------------------------------------- \n")
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