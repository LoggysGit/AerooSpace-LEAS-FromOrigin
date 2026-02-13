import asyncio
import modules.parser as fetcher # Data Parser

data_fetcher = fetcher.DataControlManager()

data_fetcher.setInput("custom", 45.9646, 63.3052, "2026-02-13T12:00:00.000000Z", "UTC+5")
asyncio.run(data_fetcher.fetchAllData())
full_prompt = data_fetcher.getFullPrompt()
print(full_prompt)

def getPrompt(type, spaceport, lat, lon, datetime, timezone):
    return full_prompt