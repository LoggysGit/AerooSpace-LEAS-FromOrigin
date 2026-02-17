import asyncio
import json
from datetime import datetime

import modules.parser as fetcher # Data Parser

input = {
    "spaceport": "Baikonur",
    "coordinates": [45.9645, 63.3055], 
    "target_timestamp": "2026-02-27T12:00:00Z",
    "timezone": "UTC+5"
}

data_fetcher = fetcher.DataControlManager()

async def getPrompt(spaceport, lat, lon, datetime, timezone):
    data_fetcher.setInput(spaceport, lat, lon, datetime, timezone)
    await data_fetcher.fetchAllData()
    full_prompt = data_fetcher.getFetchedData()
    return full_prompt

prompt = asyncio.run(getPrompt(input["spaceport"], input["coordinates"][0], input["coordinates"][1], input["target_timestamp"], input["timezone"]))
with open("test.txt", "w", encoding="utf-8") as f: f.write(json.dumps(prompt, indent=4, ensure_ascii=False))
print(json.dumps(prompt, indent=4, ensure_ascii=False))
