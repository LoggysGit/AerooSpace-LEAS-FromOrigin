from llama_cpp import Llama
import asyncio

class AIModel:
    def __init__(self, model_path, role=""):
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,  # Try to offload all layers to GPU
            n_ctx=4096,       # Context window
            verbose=False     # Disable logs for clean output
        )
        self.role = role
        self.chat_history = [{"role": "system", "content": self.role}]

    def setRole(self, role):
        self.role = role
        self.chat_history = [{"role": "system", "content": self.role}]

    async def analyze(self, prompt):
        user_message = f"{prompt}" # Formating the request with data and specific user prompt

        messages = [
            {"role": "system", "content": self.role},
            {"role": "user", "content": user_message}
        ]
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._generate, messages)
        
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
            temperature=0.7,
            max_tokens=4096
        )
        return output['choices'][0]['message']['content']