# === Dependences ===
import os
import sys

from PySide6.QtWidgets import QApplication

# === Modules ===
import modules.interface as interface

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = interface.AerooSpaceApp()
    window.show()
    sys.exit(app.exec())