# === Dependences ===
# = Libs =
import sys
import PySide6.QtWidgets as qt
# = Modules =
import modules.parser as parser     # Data Parser
import modules.controller as model  # AI Model Controller
import modules.reporter as reports  # File Manager
import modules.registrator as reg   # API Key Manager

# === Constants ===
SYSTEM_ROLE = """
You are a Lead Aerospace Flight Engineer. 
Your goal is to review launch conditions based on JSON data provided.
1. Analyze wind profiles (look for dangerous shears).
2. Check orbital debris proximity from Space-Track.
3. Evaluate space weather (radiation/magnetic risks).
4. Provide a detailed 'Go/No-Go' report and answer follow-up questions.
Be precise, technical, and critical.
"""
MODEL_PATH = "assets/model/Qwen2.5-7B-Instruct-Q4_K_M.gguf"

# === Objects & Variables ===
app = qt.QApplication(sys.argv)
data_fetcher = parser.DataControlManager()
ai = model.AIModel(MODEL_PATH, SYSTEM_ROLE)

# === App ===
# = Set the Window =
window = qt.QMainWindow()
window.setWindowTitle("LEAS FromOrigin")
window.resize(1280, 720)

# = Interface =
window.show()

# = App Loop =
sys.exit(app.exec())

# = Functions =