# === Dependences ===
# = Libs =
import sys
import PySide6.QtWidgets as qt
# = Modules =
import modules.parser as parser     # Data Parser
import modules.controller as model  # AI Model Controller
import modules.reporter as reports  # File Manager

# === Objects & Variables ===
app = qt.QApplication(sys.argv)

# === App ===
# = Set the Window

# Interfaces
label = qt.QLabel('Hello, PySide6!')
label.show()

# = App Loop =
sys.exit(app.exec())

# = Functions =