# === Dependences ===
import sys
import json
from datetime import datetime
import calendar
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QComboBox, QLineEdit, QPushButton, QScrollArea, QTextEdit)
from PySide6.QtGui import QFontDatabase, QFont, QIcon, QColor, QIntValidator
from PySide6.QtCore import Qt, QSize

# === Constants ===
ANALYTICS_PATH = "resources/analytics/"
STYLES = "assets/styles.qss"

class HistoryItem(QFrame):
    def __init__(self, title, subtitle):
        super().__init__()
        self.setFixedHeight(70)
        self.setStyleSheet(STYLE_SHEET)
        
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
    def __init__(self, file_path=f"{ANALYTICS_PATH}timestamp.json", index=0):
        super().__init__()
        self.setWindowTitle("LEAS FromOrigin - Analytics")
        self.resize(1080, 720)
        self.setStyleSheet(STYLE_SHEET)

        with open(file_path, 'r', encoding='utf-8') as f: 
            self.data_json = json.load(f)

        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        header = QHBoxLayout()
        header.addWidget(QLabel("LEAS FromOrigin"))
        header.addStretch()
        time_lbl = QLabel("2026-03-01T01:00:00Z")
        header.addWidget(time_lbl)
        main_layout.addLayout(header)

        top_row = QHBoxLayout()
        
        data_col = QVBoxLayout()
        data_col.addWidget(QLabel("Point #1\nFetched Data"))
        self.data_edit = QTextEdit()
        self.data_edit.setObjectName("DataDisplay")
        self.data_edit.setPlainText(json.dumps(self.data_json["fetched_data"][index], indent=4, ensure_ascii=False))
        self.data_edit.setReadOnly(True)
        data_col.addWidget(self.data_edit)
        top_row.addLayout(data_col, 2)

        verdict_col = QVBoxLayout()
        verdict_col.addWidget(QLabel("Verdict"))
        self.verdict_display = QTextEdit()
        self.verdict_display.setObjectName("VerdictDisplay")
        self.verdict_display.setPlainText(str(self.data_json["ai_analytics"][index]["verdict"]))
        self.verdict_display.setReadOnly(True)
        verdict_col.addWidget(self.verdict_display)
        
        self.score_label = QLabel(f"LCS: {self.data_json['ai_analytics'][index]['lcs']}")
        self.score_label.setObjectName("ScoreLabel")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verdict_col.addWidget(self.score_label)
        
        conf_lbl = QLabel(f"Prediction Confidence: {self.data_json['predictions'][index]['prediction_confidence']}%")
        conf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verdict_col.addWidget(conf_lbl)
        top_row.addLayout(verdict_col, 1)
        
        main_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()

        sim_col = QVBoxLayout()
        sim_col.addWidget(QLabel("Approximate body behaviour"))
        self.canvas_stub = QFrame()
        self.canvas_stub.setMinimumHeight(300)
        self.canvas_stub.setStyleSheet("background: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, stop:0 #002b36, stop:1 #0081a7); border-radius: 5px;")
        sim_col.addWidget(self.canvas_stub)

        input_grid = QVBoxLayout()
        for label_text, default_val in [("Mass (kg)", "10.000"), ("Density (kg/m3)", "12.345"), ("Drag coef.", "0.0123")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            line_edit = QLineEdit(default_val)
            line_edit.setFixedWidth(120)
            row.addWidget(line_edit)
            input_grid.addLayout(row)
        sim_col.addLayout(input_grid)

        sim_col.addWidget(QLabel("Risks"))
        self.risks_view = QTextEdit("• Risk 1\n• Risk 2")
        self.risks_view.setObjectName("RisksDisplay")
        self.risks_view.setMaximumHeight(100)
        sim_col.addWidget(self.risks_view)
        bottom_row.addLayout(sim_col, 1)

        chat_col = QVBoxLayout()
        chat_col.addWidget(QLabel("Model Review"))
        self.review_display = QTextEdit()
        self.review_display.setObjectName("ReviewDisplay")
        self.review_display.setReadOnly(True)
        self.review_display.setPlainText(str(self.data_json["ai_analytics"][index]["review"]))
        self.review_display.setMaximumHeight(200)
        chat_col.addWidget(self.review_display)

        chat_col.addSpacing(15)
        chat_col.addWidget(QLabel("Recommendations & Chat"))
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlainText(f"AI: {self.data_json['ai_analytics'][index]['recommendations']}")
        chat_col.addWidget(self.chat_display)

        chat_input_area = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Input your request...")
        
        send_btn = QPushButton("➤")
        send_btn.setObjectName("SendBtn")
        send_btn.setFixedWidth(50)
        
        chat_input_area.addWidget(self.chat_input)
        chat_input_area.addWidget(send_btn)
        chat_input_area.setSpacing(0)
        chat_col.addLayout(chat_input_area)

        bottom_row.addLayout(chat_col, 1)
        main_layout.addLayout(bottom_row)

        scroll.setWidget(container)
        window_layout.addWidget(scroll)

    def append_to_review(self, text):
        self.chat_display.append(f"\n{text}")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

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
        line.setStyleSheet("background-color: #3d3d3d; max-height: 1px; margin: 10px 0; border: none;")
        container_layout.addWidget(line)

    def setup_input_ui(self, parent_layout, point_id):
        point_container = QWidget()
        point_container.setObjectName(f"point_{point_id}")
        container_layout = QVBoxLayout(point_container)
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
            btn_del.clicked.connect(lambda: self.remove_point(point_container))
            header_layout.addWidget(btn_del)

        container_layout.addLayout(header_layout)
        self.spaceport_combo = QComboBox()
        self.add_single_field(container_layout, "Spaceport", self.spaceport_combo)
        self.spaceport_combo.addItem("custom")
        
        row_coords = QHBoxLayout()
        self.latitude_coord = QLineEdit("43.3543")
        self.longitude_coord = QLineEdit("77.0224")
        self.add_field_to_layout(row_coords, "Latitude", self.latitude_coord)
        self.add_field_to_layout(row_coords, "Longitude", self.longitude_coord)
        container_layout.addLayout(row_coords)
        
        row_date = QHBoxLayout()
        current_y = datetime.now().year
        year_edit = QLineEdit(str(current_y))
        year_edit.setFixedWidth(60)
        self.add_field_to_layout(row_date, "Year", year_edit)
        
        month_edit = QLineEdit("02")
        month_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Month", month_edit)
        
        day_edit = QLineEdit("14")
        day_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "Day", day_edit)
        
        utc_label = QLabel("UTC")
        utc_label.setFixedWidth(60)
        row_date.addWidget(utc_label)
        tz_edit = QLineEdit("+0")
        tz_edit.setFixedWidth(45)
        self.add_field_to_layout(row_date, "TZ", tz_edit)
        
        container_layout.addLayout(row_date)
        parent_layout.insertWidget(parent_layout.count() - 1, point_container)

    def add_point(self):
        if self.points_count < 3:
            self.points_count += 1
            self.setup_input_ui(self.points_layout, self.points_count)
            if self.points_count >= 3: self.btn_add.hide()

    def remove_point(self, widget):
        widget.deleteLater()
        self.points_count -= 1
        if self.points_count < 3: self.btn_add.show()

    def show_loading(self):
        pass
    def hide_loading(self):
        pass

    def show_analytics_window(self, path):
        self.analytics_window = AnalyticsWindow(path)
        self.analytics_window.show()

    def start_analyzing(self):
        self.show_loading()
        # Collect data from points
        
        # Send to prompter

        # Save result in file

        # Show result
        self.hide_loading()
        analytics_path = {ANALYTICS_PATH} + f"{0}.json"
        self.show_analytics_window(analytics_path)
        pass

    def init_ui(self):
        self.setWindowTitle("AerooSpace LEAS")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE_SHEET)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(40)

        # LEFT
        analytics_block = QVBoxLayout()
        lbl_create = QLabel("Create Analytics")
        lbl_create.setObjectName("Header")
        analytics_block.addWidget(lbl_create)

        panel_left = QFrame()
        panel_left.setObjectName("Panel")
        analytics_block_layout = QVBoxLayout(panel_left)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.points_layout = QVBoxLayout(scroll_content)
        self.points_layout.setSpacing(20)
        scroll_area.setWidget(scroll_content)
        analytics_block_layout.addWidget(scroll_area)

        self.points_count = 0
        self.btn_add = QPushButton("+")
        self.btn_add.clicked.connect(self.add_point)
        self.add_point()
        self.points_layout.addWidget(self.btn_add)

        btn_analyse = QPushButton("Analyse")
        btn_analyse.setObjectName("AnalyseBtn")
        btn_analyse.clicked.connect(self.show_analytics_window)
        analytics_block_layout.addWidget(btn_analyse)
        analytics_block.addWidget(panel_left)

        # RIGHT
        right_container = QVBoxLayout()
        lbl_history = QLabel("History")
        lbl_history.setObjectName("Header")
        right_container.addWidget(lbl_history)

        panel_right = QFrame()
        panel_right.setObjectName("Panel")
        right_panel_layout = QVBoxLayout(panel_right)
        scroll_hist = QScrollArea()
        scroll_hist.setWidgetResizable(True)
        scroll_hist_content = QWidget()
        self.history_layout = QVBoxLayout(scroll_hist_content)
        self.history_layout.setAlignment(Qt.AlignTop)
        scroll_hist.setWidget(scroll_hist_content)
        right_panel_layout.addWidget(scroll_hist)
        right_container.addWidget(panel_right)

        main_layout.addLayout(analytics_block, 1)
        main_layout.addLayout(right_container, 1)

if __name__ == "__main__":
    with open(STYLES, "r", encoding="utf-8") as f: STYLE_SHEET = f.read()
    app = QApplication(sys.argv)
    window = AerooSpaceApp()
    window.show()
    sys.exit(app.exec())