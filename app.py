# === Dependences ===
import os
import sys

from PySide6.QtWidgets import QApplication

import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# === Modules ===
import modules.interface as interface

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = interface.AerooSpaceApp()
    window.show()
    sys.exit(app.exec())