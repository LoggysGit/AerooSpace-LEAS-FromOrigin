import sys
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QFrame, QLabel, QComboBox, QLineEdit, QPushButton, 
                             QScrollArea, QSpacerItem, QSizePolicy, QStackedWidget)
from PySide6.QtGui import QFontDatabase, QFont, QIcon, QColor, QIntValidator
from PySide6.QtCore import Qt, QSize

from datetime import datetime
import calendar

# --- Стили QSS (Темная тема) ---
STYLE_SHEET = """
QWidget {
    background-color: #121212;
    color: #FFFFFF;
}
QFrame#Panel {
    background-color: #1E1E1E;
    border: 1px solid #333333;
}
QLabel#Header {
    font-family: 'Krona One';
    font-size: 24px;
    margin-bottom: 10px;
}
QLabel#Label {
    font-family: 'JetBrains Mono';
    font-size: 12px;
    color: #888888;
}
QLineEdit, QComboBox {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
    padding: 10px;
    font-family: 'JetBrains Mono';
    font-size: 14px;
    color: #FFFFFF;
}
QPushButton#AnalyseBtn {
    background-color: #FFFFFF;
    color: #000000;
    font-family: 'Krona One';
    font-size: 18px;
    padding: 15px;
    margin-top: 20px;
}
QPushButton#AnalyseBtn:hover {
    background-color: #E0E0E0;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""

class HistoryItem(QFrame):
    """Виджет одной строки в истории"""
    def __init__(self, title, subtitle):
        super().__init__()
        self.setFixedHeight(70)
        self.setStyleSheet("""
            QFrame {
                background-color: #252525;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #2D2D2D;
                border: 1px solid #444444;
            }
        """)
        
        layout = QHBoxLayout(self)
        
        text_layout = QVBoxLayout()
        name = QLabel(title)
        name.setFont(QFont("JetBrains Mono", 12, QFont.Bold))
        name.setStyleSheet("background: transparent; border: none;")
        
        info = QLabel(subtitle)
        info.setFont(QFont("JetBrains Mono", 10))
        info.setStyleSheet("color: #666666; background: transparent; border: none;")
        
        text_layout.addWidget(name)
        text_layout.addWidget(info)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Кнопки управления (заглушки)
        for icon_text in ["🔄", "🗑️"]:
            btn = QPushButton(icon_text)
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("background: #333; font-size: 14px;")
            layout.addWidget(btn)


class AerooSpaceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.load_fonts()
        self.init_ui()

    def load_fonts(self):
        QFontDatabase.addApplicationFont("assets/fonts/KronaOne.ttf")
        QFontDatabase.addApplicationFont("assets/fonts/JetBrainsMono/JetBrainsMono-Regular.ttf")

    def add_field_to_layout(self, layout, label_text, widget):
        container = QVBoxLayout()
        if label_text != None:
            lbl = QLabel(label_text)
            lbl.setObjectName("Label")
            container.addWidget(lbl)
        container.addWidget(widget)
        layout.addLayout(container)

    def add_single_field(self, parent_layout, label_text, widget):
        self.add_field_to_layout(parent_layout, label_text, widget)

    def load_spaceports(self, combo):
        pass

    def fix_range(self, widget, min_val, max_val):
        try:
            current_text = widget.text().strip()
            if not current_text:
                widget.setText(str(min_val))
                return
            val = float(current_text)
            if val < min_val: widget.setText(str(min_val))
            elif val > max_val: widget.setText(str(max_val))
            else:
                if val == int(val): widget.setText(str(int(val)))
                else: widget.setText(str(val))
        except ValueError:
            widget.setText(str(min_val))

    def setup_analytics_ui(self, parent_layout, point_index):
        # Spaceport
        self.spaceport_combo = QComboBox()
        self.add_single_field(parent_layout, "Spaceport", self.spaceport_combo)
        self.spaceport_combo.addItem("custom")
        self.load_spaceports(self.spaceport_combo)
        
        # Coordinates - Lat & Lon
        row_coords = QHBoxLayout()
        self.latitude_coord = QLineEdit("43.3543")
        self.longitude_coord = QLineEdit("77.0224")
        self.add_field_to_layout(row_coords, "Latitude", self.latitude_coord)
        self.add_field_to_layout(row_coords, "Longitude", self.longitude_coord)
        self.latitude_coord.setMaxLength(7)
        self.longitude_coord.setMaxLength(7)
        parent_layout.addLayout(row_coords)
        
        # - Full Time -
        row_time = QHBoxLayout()
        row_time.setSpacing(10)
         # Date
        row_date = QHBoxLayout()
        row_date.setSpacing(10)
         # Year
        current_y = datetime.now().year
        y_window = 100
        self.year_edit = QLineEdit(str(current_y))
        self.year_edit.setMaxLength(4)
        self.year_edit.editingFinished.connect(
            lambda: self.fix_range(self.year_edit, current_y, current_y + y_window)
        )
        self.year_edit.setFixedWidth(60)
        self.add_field_to_layout(row_date, "Year", self.year_edit)
         # Month
        self.month_edit = QLineEdit("02")
        self.month_edit.setMaxLength(2)
        self.month_edit.editingFinished.connect(
            lambda: self.fix_range(self.month_edit, 1, 12)
        )
        self.month_edit.editingFinished.connect(
            lambda: self.fix_range(
                self.day_edit, 1, 
                calendar.monthrange(int(self.year_edit.text()), int(self.month_edit.text()))[1]
            )
        )
        self.month_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Month", self.month_edit)
         # Day
        self.day_edit = QLineEdit("14")
        self.day_edit.setMaxLength(2)
        self.day_edit.editingFinished.connect(
            lambda: self.fix_range(
                self.day_edit, 1, 
                calendar.monthrange(int(self.year_edit.text()), int(self.month_edit.text()))[1]
            )
        )
        self.day_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Day", self.day_edit)
        parent_layout.addLayout(row_date)

        # UTC Block
        utc_label = QLabel("UTC")
        utc_label.setStyleSheet("color: #666; margin-top: 20px; font-family: 'JetBrains Mono';")
        utc_label.setFixedWidth(60)
        row_date.addWidget(utc_label)
        tz_edit = QLineEdit("+0")
        tz_edit.setFixedWidth(45)
        tz_edit.setAlignment(Qt.AlignCenter)
        self.add_field_to_layout(row_date, "TZ", tz_edit)

        row_time.addLayout(row_date)
        
        parent_layout.addLayout(row_time)

    def init_ui(self):
        self.setWindowTitle("AerooSpace LEAS")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE_SHEET)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(40)

        # --- ANALYTICS BLOCK ---
        analytics_block = QVBoxLayout()
        
        lbl_create = QLabel("Create Analytics")
        lbl_create.setObjectName("Header")
        analytics_block.addWidget(lbl_create)

        panel_left = QFrame()
        panel_left.setObjectName("Panel")
        analytics_block_layout = QVBoxLayout(panel_left)
        analytics_block_layout.setContentsMargins(30, 30, 30, 30)
        analytics_block_layout.setSpacing(15)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        points = QVBoxLayout(scroll_content)
        points.setSpacing(15)
        points.setContentsMargins(10, 10, 10, 10)

        scroll_area.setWidget(scroll_content)

        analytics_block_layout.addWidget(scroll_area)

        for i in range(1):
            self.setup_analytics_ui(points, i)
            if i > 0:
                div = QLabel("---------------------------------------------------------------------")
                points.addWidget(div)

        btn_add = QPushButton("+")
        points.addWidget(btn_add)

        btn_analyse = QPushButton("Analyse")
        btn_analyse.setObjectName("AnalyseBtn")
        btn_analyse.setCursor(Qt.PointingHandCursor)
        analytics_block_layout.addWidget(btn_analyse)
        analytics_block_layout.addStretch()

        analytics_block.addWidget(panel_left)


        # --- HISTORY ---
        right_container = QVBoxLayout()
        
        lbl_history = QLabel("History")
        lbl_history.setObjectName("Header")
        right_container.addWidget(lbl_history)

        panel_right = QFrame()
        panel_right.setObjectName("Panel")
        right_panel_layout = QVBoxLayout(panel_right)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.history_layout = QVBoxLayout(self.scroll_content)
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_layout.setSpacing(10)

        # Тестовые данные в историю
        self.history_layout.addWidget(HistoryItem("Almaty Intl (UAAA)", "Feb 14, 2026 • 10:52 • PR: Successful"))
        self.history_layout.addWidget(HistoryItem("Dubai Intl (OMDB)", "Feb 13, 2026 • 22:15 • PR: Warning"))
        self.history_layout.addWidget(HistoryItem("Baikonur (UAON)", "Feb 10, 2026 • 09:00 • PR: Critical"))

        self.scroll.setWidget(self.scroll_content)
        right_panel_layout.addWidget(self.scroll)

        right_container.addWidget(panel_right)

        #main_layout.add
        # ADD BOTH TO A MAIN LAYOUT
        main_layout.addLayout(analytics_block, 1)
        main_layout.addLayout(right_container, 1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AerooSpaceApp()
    window.show()
    sys.exit(app.exec())