# === Dependences ===
# = Libs =
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtWidgets import QPushButton
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
data_fetcher = parser.DataControlManager()
ai = model.AIModel(MODEL_PATH, SYSTEM_ROLE)

# === App ===
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LEAS FromOrigin")
        self.resize(1280, 720)

        # Styles
        self.load_styles("assets/styles.qss")

        # Main Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Pages Stack
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)

        # Pages
        self.page_input = self.init_input_page()
        self.page_analysis = self.init_analysis_page()
        self.page_settings = self.init_settings_page()

        self.pages.addWidget(self.page_input)
        self.pages.addWidget(self.page_analysis)
        self.pages.addWidget(self.page_settings)

    def load_styles(self, filename):
        try:
            with open(filename, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Error reading styles: {filename}")

    # --- PAGES ---
    def init_input_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        btn = QPushButton("Analysis")
        btn.setObjectName("mainButton") # ID для стилей
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        layout.addWidget(btn)

        return page

    def init_analysis_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        btn = QPushButton("Setting")
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        layout.addWidget(btn)

        return page

    def init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        btn = QPushButton("Back")
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        layout.addWidget(btn)

        return page

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())