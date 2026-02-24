# === Dependences ===
import os

class Logger:
    def __init__(self, journal_path): 
        self.journal_path = journal_path
        self.journal_started = False
        self.content = ""

    def start_log(self):
        self.journal_started = True

    def write(self, text):
        self.content += str(text) + "\n" 
        print(text)

    def throwError(self, error):
        pass

    def save(self, file_name="journal_12345678.log"):
        full_path = os.path.join(self.journal_path, f"{file_name}.txt")
        try:
            with open(full_path, "w", encoding="utf-8") as f: f.write(self.content)
            self.content = ""
            self.journal_started = False
        except Exception as e: self.throwError(f"Failed to save log: {e}")