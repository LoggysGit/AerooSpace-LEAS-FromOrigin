from llama_cpp import Llama
import asyncio

class AIModel:
    def __init__(self, model_path, role):
        # Setting up the model for your RTX 3050 (4GB VRAM)
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,  # Try to offload all layers to GPU
            n_ctx=4096,       # Context window for large JSON data
            verbose=False     # Disable logs for clean output
        )
        self.role = role
        self.chat_history = [{"role": "system", "content": self.role}]

    async def analyze(self, data, prompt):
        """
        One-shot analysis of provided aerospace data.
        """
        # Formating the request with data and specific user prompt
        user_message = f"DATA: {data}\n\nQUESTION: {prompt}"
        
        # We don't save analysis to history to keep context clean for chatting
        messages = [
            {"role": "system", "content": self.role},
            {"role": "user", "content": user_message}
        ]
        
        # Running in a thread pool to avoid freezing the PySide6 UI
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._generate, messages)
        
        return response

    async def ask(self, prompt):
        """
        Continuous dialogue (review review, consulting).
        """
        self.chat_history.append({"role": "user", "content": prompt})
        
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, self._generate, self.chat_history)
        
        self.chat_history.append({"role": "assistant", "content": answer})
        return answer

    def _generate(self, messages):
        """
        Internal sync method for generation.
        """
        output = self.llm.create_chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        return output['choices'][0]['message']['content']