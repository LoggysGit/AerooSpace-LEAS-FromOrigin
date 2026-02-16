import sys
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QFrame, QLabel, QComboBox, QLineEdit, QPushButton, 
                             QScrollArea, QSpacerItem, QSizePolicy, QStackedWidget, QTextEdit)
from PySide6.QtGui import QFontDatabase, QFont, QIcon, QColor, QIntValidator
from PySide6.QtCore import Qt, QSize

from datetime import datetime
import calendar

import asyncio

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

QPushButton#DeletePointBtn { 
    background: #442222; color: white; border: none; 
}
QPushButton#DeletePointBtn:hover { background: #ff4444; }
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

        for icon_text in ["🔄", "🗑️"]:
            btn = QPushButton(icon_text)
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("background: #333; font-size: 14px;")
            layout.addWidget(btn)

class AnalyticsWindow(QWidget):
    def __init__(self, analytics_data):
        super().__init__()
        self.data = analytics_data
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AerooSpace LEAS - Detailed Analysis")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE_SHEET)

        layout = QVBoxLayout(self)

        header = QLabel("Analysis Results")
        header.setObjectName("Header")
        layout.addWidget(header)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setText(str(self.data))
        layout.addWidget(self.result_view)

        btn_back = QPushButton("Back to Setup")
        btn_back.clicked.connect(self.close)
        layout.addWidget(btn_back)

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

    def create_divider(self, container_layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("""
            background-color: #3d3d3d; 
            max-height: 1px; 
            margin: 10px 0;
            border: none;
        """)
        container_layout.addWidget(line)

    def setup_input_ui(self, parent_layout, point_id):
        point_container = QWidget()
        point_container.setObjectName(f"point_{point_id}")
        container_layout = QVBoxLayout(point_container)
        container_layout.setContentsMargins(0, 5, 0, 5)

        header_layout = QHBoxLayout()
        lbl = QLabel(f"LOCATION #{point_id}")
        lbl.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(lbl)

        header_layout.addStretch()

        if point_id > 1:
            self.create_divider(container_layout)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(40, 40)
            btn_del.setCursor(Qt.PointingHandCursor)

            btn_del.setObjectName("DeletePointBtn")
            btn_del.style().unpolish(btn_del)
            btn_del.style().polish(btn_del)

            btn_del.clicked.connect(lambda: self.remove_point(point_container))
            header_layout.addWidget(btn_del)

        container_layout.addLayout(header_layout)

        # Spaceport
        self.spaceport_combo = QComboBox()
        self.add_single_field(container_layout, "Spaceport", self.spaceport_combo)
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
        container_layout.addLayout(row_coords)
        
        # - Full Time -
        row_time = QHBoxLayout()
        row_time.setSpacing(10)
         # Date
        row_date = QHBoxLayout()
        row_date.setSpacing(10)
         # Year
        current_y = datetime.now().year
        y_window = 100
        year_edit = QLineEdit(str(current_y))
        year_edit.setMaxLength(4)
        year_edit.editingFinished.connect(
            lambda: self.fix_range(year_edit, current_y, current_y + y_window)
        )
        year_edit.setFixedWidth(60)
        self.add_field_to_layout(row_date, "Year", year_edit)
         # Month
        month_edit = QLineEdit("02")
        month_edit.setMaxLength(2)
        month_edit.editingFinished.connect(
            lambda: self.fix_range(month_edit, 1, 12)
        )
        month_edit.editingFinished.connect(
            lambda: self.fix_range(
                day_edit, 1, 
                calendar.monthrange(int(year_edit.text()), int(month_edit.text()))[1]
            )
        )
        month_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Month", month_edit)
         # Day
        day_edit = QLineEdit("14")
        day_edit.setMaxLength(2)
        day_edit.editingFinished.connect(
            lambda: self.fix_range(
                day_edit, 1, 
                calendar.monthrange(int(year_edit.text()), int(month_edit.text()))[1]
            )
        )
        day_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Day", day_edit)
        container_layout.addLayout(row_date)

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
        
        container_layout.addLayout(row_time)

        parent_layout.insertWidget(parent_layout.count() - 1, point_container)

    def add_point(self):
        if self.points_count < 3:
            self.points_count += 1

            self.setup_input_ui(self.points_layout, self.points_count)

            if self.points_count >= 3: self.btn_add.hide()
            #else: self.btn_add.show()

    def remove_point(self, widget):
        widget.deleteLater()
        self.points_count -= 1
        if self.points_count < 3: self.btn_add.show()

    def show_analytics_window(self):
        #input_data = self.collect_points_data() 
        self.analytics_window = AnalyticsWindow("{\nData\n}")
        self.analytics_window.show()

    def start_analysing(self):
        self.show_analytics_window()

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
        points.setSpacing(20)
        points.setContentsMargins(10, 10, 10, 80)

        scroll_area.setWidget(scroll_content)

        analytics_block_layout.addWidget(scroll_area)

        # POINTS
        self.points_layout = points 
        self.points_count = 0

        self.btn_add = QPushButton("+")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setObjectName("AddBtn")

        self.add_point() 

        self.btn_add.clicked.connect(self.add_point)
        self.points_layout.addWidget(self.btn_add)

        # START ANALYSING
        btn_analyse = QPushButton("Analyse")
        btn_analyse.setObjectName("AnalyseBtn")
        btn_analyse.setCursor(Qt.PointingHandCursor)
        btn_analyse.clicked.connect(self.show_analytics_window)

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

        self.scroll.setWidget(self.scroll_content)
        right_panel_layout.addWidget(self.scroll)

        right_container.addWidget(panel_right)

        #main_layout.add
        # ADD BOTH TO A MAIN LAYOUT
        main_layout.addLayout(analytics_block, 1)
        main_layout.addLayout(right_container, 1)

    def init_analytics_window(self, analytics_name):
        self.setWindowTitle(f"AerooSpace LEAS - Analytics")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE_SHEET)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(40)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AerooSpaceApp()
    window.show()
    sys.exit(app.exec())