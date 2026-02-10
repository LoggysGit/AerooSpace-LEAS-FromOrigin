import asyncio
# = Modules =
import modules.parser as parser     # Data Parser
import modules.controller as model  # AI Model Controller
import modules.reporter as reports  # File Manager
import modules.registrator as reg   # API Key Manager

# === Constants ===
MODEL_PATH = "assets/model/Qwen2.5-7B-Instruct-Q4_K_M.gguf"

# === Objects & Variables ===
ai = model.AIModel(MODEL_PATH)
data_fetcher = parser.DataControlManager()

# === Test ===
data_fetcher.setInput("custom", 45.9646, 63.3052, "2026-02-13T12:00:00.000000Z", "UTC+5")
asyncio.run(data_fetcher.fetchAllData())
full_prompt = data_fetcher.getFullPrompt()
print(full_prompt)

ai.setRole("")
#ai.analyze(full_prompt)