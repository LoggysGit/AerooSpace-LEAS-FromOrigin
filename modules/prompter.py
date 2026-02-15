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
        "coordinates": [71.6872, 128.8536],
        "target_timestamp": "2026-02-21T12:00:00Z",
        "timezone": "UTC+0"
    },
    {
        "spaceport": "custom",
        "coordinates": [-16.5000, -68.1193],
        "target_timestamp": "2026-02-22T12:00:00Z",
        "timezone": "UTC+0"
    },
    {
        "spaceport": "custom",
        "coordinates": [1.3521, 103.8198],
        "target_timestamp": "2026-01-25T12:00:00Z",
        "timezone": "UTC+0"
    }
]

async def analyseAllPoints(inputs):
    with open(PROMPTS_JSON_PATH, 'r', encoding='utf-8') as f: prompts = json.load(f)
    ai.setRole(prompts["role"])

    fetched, analytics = [], []
    for input in inputs:
        print(" ========== STARTING POINT ANALYSIS... ========== ")
        prompt = await getPrompt(input["spaceport"], input["coordinates"][0], input["coordinates"][1], input["target_timestamp"], input["timezone"],)
        fetched.append(data_fetcher.getFetchedData())
        review = await ai.analyze(prompt)
        analytics.append(review)

    if len(inputs) > 1:
        comp_prompt = getComparsionPrompt(inputs, fetched, analytics)

    print(fetched)
    print("\n -------------------------------------------------------------------------------- \n")
    print(analytics)
    print("\n -------------- \n")

    print(datetime.now())

def compare(prompt):
    pass

# Test
asyncio.run(analyseAllPoints(inps))