import asyncio
import json
import os
# = Modules =
import modules.prompter as prompter     # Data Parser
import modules.controller as model  # AI Model Controller
import modules.reporter as reports  # File Manager

# === Constants ===
MODEL_PATH = "assets/model/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
PROMPTS_JSON_PATH = "resources/prompts.json"

# === Objects & Variables ===
ai = model.AIModel(MODEL_PATH)

# === Test ===