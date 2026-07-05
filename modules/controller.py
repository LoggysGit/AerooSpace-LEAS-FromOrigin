import os

from llama_cpp import Llama, hf_hub_download
import asyncio

import modules.lib as lib

class XGBModel:
    def __init__(self):
        pass

class AIModel:
    def __init__(self, model_path, role=""):
        self.get_model()
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=8,
            n_ctx=32768,
            verbose=False
        )
        self.role = role
        self.chat_history = [{"role": "system", "content": self.role}]

    def get_model():
        if os.path.exists(lib.MODEL_PATH):
            lib.update_settings(True)
            return lib.MODEL_PATH

        lib.log(f"MODEL NOT FOUND IN {lib.MODEL_PATH}. DOWNLOADING FROM HUGGING FACE...")

        try:
            path = hf_hub_download(
                repo_id=lib.LLM_REPO_ID,
                filename=lib.LLM_NAME,
                local_dir=lib.MODEL_PATH,
                local_dir_use_symlinks=False
            )
            lib.log("\nSUCCESS: Model installed.")
            lib.update_settings(True)
            return path
        except Exception as e:
            lib.log(f"\nFATAL ERROR during download: {e}")
            lib.update_settings(False)
            return None

    def setRole(self, role):
        self.role = role
        self.chat_history = [{"role": "system", "content": self.role}]

    async def analyze(self, prompt):
        user_message = f"{prompt}" # Formating the request with data and specific user prompt

        messages = [
            {"role": "system", "content": self.role},
            {"role": "user", "content": user_message}
        ]

        lib.log("[AI] Start Analysing...")
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._generate, messages)
        
        lib.log("[AI] Success! Analytics finished.\n")

        return response

    async def ask(self, prompt):
        self.chat_history.append({"role": "user", "content": prompt}) # Add prompt to history
        
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, self._generate, self.chat_history)
        
        self.chat_history.append({"role": "assistant", "content": answer}) # Add answer to history
        return answer

    def _generate(self, messages):
        output = self.llm.create_chat_completion(
            messages=messages,
            temperature=0.01,
            max_tokens=2048
        )
        return output['choices'][0]['message']['content']