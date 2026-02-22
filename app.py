# === Dependences ===
import os
import sys
import json
import asyncio
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
import calendar
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QComboBox, QLineEdit, QPushButton, QScrollArea, QTextEdit)
from PySide6.QtGui import QFontDatabase, QFont, QDoubleValidator
from PySide6.QtCore import Qt, Signal, QThread, QEasingCurve, QRect
# === Modules ===
import modules.prompter as prompter
import modules.simulator as simulator

# === Constants ===
STYLES = "assets/styles.qss"
REPORTS_PATH= "resources/reports/"

class HistoryItem(QFrame):
    delete_requested = Signal(str)
    refresh_requested = Signal(str)
    open_requested = Signal(str)

    def __init__(self, path, title, subtitle):
        super().__init__()
        self.path = path
        self.setFixedHeight(70)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        text_layout = QVBoxLayout()
        
        name = QLabel(title)
        name.setFont(QFont("JetBrains Mono", 11, QFont.Bold))
        name.setStyleSheet("background: transparent; color: white;")
        
        info = QLabel(subtitle)
        info.setFont(QFont("JetBrains Mono", 9))
        info.setStyleSheet("color: #888; background: transparent;")
        
        text_layout.addWidget(name)
        text_layout.addWidget(info)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Action Buttons
        for icon, signal in [("⟳", self.refresh_requested), ("✖", self.delete_requested)]:
            btn = QPushButton(icon)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("background: #333; border-radius: 4px; color: white;")
            btn.clicked.connect(lambda checked=False, s=signal: s.emit(self.path))
            layout.addWidget(btn)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.open_requested.emit(self.path)
        super().mousePressEvent(event)

class AnalysisWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, mission_input, prompter):
        super().__init__()
        self.mission_input = mission_input
        self.prompter = prompter

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            file_name = loop.run_until_complete(self.prompter.analyseAllPoints(self.mission_input))
            
            loop.close()
            self.finished.emit(file_name)
        except Exception as e: self.error.emit(str(e))

class AerooLoadingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(300, 300)
        self.setWindowTitle("Analytics in progress...")

        self.setWindowFlags(
            Qt.Window | 
            Qt.CustomizeWindowHint | 
            Qt.WindowMinimizeButtonHint | 
            Qt.WindowStaysOnTopHint
        )

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #333333;
            }
        """)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel("ANALYSIS IN PROGRESS...\nPLEASE WAIT")
        self.label.setObjectName("Label")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            color: #f0f0f0;
            font-family: 'JetBrains Mono';
            font-size: 13px;
            font-weight: bold;
            background: transparent;
        """)

        self.container_layout.addWidget(self.label)
        self.layout.addWidget(self.container)

    def showEvent(self, event): super().showEvent(event)

    def closeEvent(self, event): event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: event.ignore()
        else: super().keyPressEvent(event)

class AnalyticsWindow(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.setWindowTitle("LEAS FromOrigin - Analytics")
        self.resize(1080, 720)
        self.setStyleSheet(STYLE_SHEET)

        with open(file_path, 'r', encoding='utf-8') as f: self.data_json = json.load(f)
        print(file_path)

        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        for index in range(self.data_json["point_count"]):
            container = QWidget()
            main_layout = QVBoxLayout(container)
            main_layout.setContentsMargins(30, 30, 30, 30)
            main_layout.setSpacing(25)

            header = QHBoxLayout()
            header.addWidget(QLabel("LEAS FromOrigin"))
            header.addWidget(QLabel(f"Point#{index+1}"))
            header.addStretch()
            time_lbl = QLabel("2026-03-01T01:00:00Z")
            header.addWidget(time_lbl)
            main_layout.addLayout(header)

            top_row = QHBoxLayout()

            data_col = QVBoxLayout()
            data_col.addWidget(QLabel("Fetched Data"))
            self.data_edit = QTextEdit()
            self.data_edit.setObjectName("DataDisplay")
            self.data_edit.setPlainText(json.dumps(self.data_json["fetched"][index], indent=4, ensure_ascii=False))
            self.data_edit.setReadOnly(True)
            data_col.addWidget(self.data_edit)
            top_row.addLayout(data_col, 2)

            verdict_col = QVBoxLayout()
            verdict_col.addWidget(QLabel("Verdict"))
            self.verdict_display = QTextEdit()
            self.verdict_display.setObjectName("VerdictDisplay")
            self.verdict_display.setPlainText(str(self.data_json["analytics"][index]["verdict"]))
            self.verdict_display.setReadOnly(True)
            verdict_col.addWidget(self.verdict_display)

            self.score_label = QLabel(f"LCS: {self.data_json['analytics'][index]['lcs']}")
            self.score_label.setObjectName("ScoreLabel")
            self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            verdict_col.addWidget(self.score_label)

            conf_lbl = QLabel(f"Prediction Confidence: {self.data_json['predicted'][index]['prediction_confidence']}%")
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
            self.review_display.setPlainText(str(self.data_json["analytics"][index]["review"]))
            self.review_display.setMaximumHeight(200)
            chat_col.addWidget(self.review_display)

            chat_col.addSpacing(15)
            chat_col.addWidget(QLabel("Recommendations & Chat"))
            self.chat_display = QTextEdit()
            self.chat_display.setObjectName("ChatDisplay")
            self.chat_display.setReadOnly(True)
            self.chat_display.setPlainText(f"AI: {self.data_json['analytics'][index]['recommendations']}")
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

    point_containers = []

    def load_fonts(self):
        QFontDatabase.addApplicationFont("assets/fonts/KronaOne.ttf")
        QFontDatabase.addApplicationFont("assets/fonts/JetBrainsMono/JetBrainsMono-Regular.ttf")

    def setup_spaceports(self, combo):
        SPACEPORT_PATH = "resources/spaceports.json"
        combo.addItem("custom", "custom")
        try:
            with open(SPACEPORT_PATH, "r", encoding="utf-8") as f: self.spaceports_data = json.load(f)
            for name in self.spaceports_data.keys():
                display_name = name.replace("_", " ")
                combo.addItem(display_name, name)
        except Exception as e:
            print(f"[A] Error loading spaceports: {e}")
            self.spaceports_data = {}
    def handle_spaceport_combo(self, combo, lat_inp, lon_inp, tz_inp, index):
        key = combo.itemData(index)

        if key and key in self.spaceports_data and key != "custom":
            data = self.spaceports_data[key]
            lat, lon = data["coordinates"]

            lat_inp.setText(str(lat))
            lon_inp.setText(str(lon))

            lat_inp.setReadOnly(True)
            lon_inp.setReadOnly(True)

            lat_inp.setStyleSheet("background-color: #2b2b2b; color: #888;")
            lon_inp.setStyleSheet("background-color: #2b2b2b; color: #888;")

            if "timezone" in data: tz_inp.setText(data["timezone"])
            else: self.update_tz(lat_inp, lon_inp, tz_inp)
        else:
            lat_inp.setStyleSheet("background-color: #1e1e1e; color: white; border: 1px solid #3d3d3d;")
            lon_inp.setStyleSheet("background-color: #1e1e1e; color: white; border: 1px solid #3d3d3d;")

            lat_inp.setReadOnly(False)
            lon_inp.setReadOnly(False)

    def add_field_to_layout(self, layout, label_text, widget):
        container = QVBoxLayout()
        if label_text != None:
            lbl = QLabel(label_text)
            lbl.setObjectName("Label")
            container.addWidget(lbl)
        container.addWidget(widget)
        layout.addLayout(container)

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

    def get_last_day(self, y, m): return calendar.monthrange(y, m)[1]

    def update_tz(self, lat_field, lon_field, tz_field):
        try:
            lat = lat_field.text()
            lng = lon_field.text()

            tf = TimezoneFinder()

            timezone_str = tf.timezone_at(lng=float(lng), lat=float(lat))
            
            if timezone_str is None: return "+0"
            timezone = pytz.timezone(timezone_str)
            dt = datetime.now()
            offset_seconds = timezone.utcoffset(dt).total_seconds()
            offset_hours = int(offset_seconds / 3600)
            
            tz_field.setText(f"+{offset_hours}" if offset_hours >= 0 else str(offset_hours))
        except: pass
            
    def create_divider(self, container_layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #3d3d3d; max-height: 1px; margin: 10px 0; border: none;")
        container_layout.addWidget(line)

    def refresh_history(self):
        while self.history_layout.count():
            child = self.history_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        if not os.path.exists(REPORTS_PATH):
            os.makedirs(REPORTS_PATH)
            return

        # Filter and sort files by timestamp (Newest first)
        files = [os.path.join(REPORTS_PATH, f) for f in os.listdir(REPORTS_PATH) if f.endswith('.json')]
        files.sort(key=os.path.getmtime, reverse=True)

        for f_path in files:
            name = os.path.basename(f_path)
            mtime = os.path.getmtime(f_path)
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

            item = HistoryItem(f_path, name, date_str)

            item.delete_requested.connect(self.delete_report)
            item.refresh_requested.connect(self.refresh_report_data)
            item.open_requested.connect(lambda path=f_path: self.show_analytics_window(path))

            self.history_layout.addWidget(item)

        self.history_layout.addStretch()

    def delete_report(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
                self.refresh_history()
        except Exception as e: print(f"File deletion failed: {e}")

    def refresh_report_data(self, path):
        pass

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
        spaceport_combo = QComboBox()
        spaceport_combo.setObjectName("spaceport_input")
        self.add_field_to_layout(container_layout, "Spaceport", spaceport_combo)
        self.setup_spaceports(spaceport_combo)
        spaceport_combo.currentIndexChanged.connect(lambda i: self.handle_spaceport_combo(spaceport_combo, latitude_coord, longitude_coord, tz_edit, i))
        
        row_coords = QHBoxLayout()
        latitude_coord = QLineEdit("28.3922")
        longitude_coord = QLineEdit("-80.6077")
        latitude_coord.setObjectName("lat_input")
        longitude_coord.setObjectName("lon_input")
        latitude_coord.editingFinished.connect(lambda: self.update_tz(latitude_coord, longitude_coord, tz_edit))
        longitude_coord.editingFinished.connect(lambda: self.update_tz(latitude_coord, longitude_coord, tz_edit))
        
        #coord_validator = QDoubleValidator(-180.0, 180.0, 4)
        #coord_validator.setNotation(QDoubleValidator.StandardNotation)
        #latitude_coord.setValidator(coord_validator)
        #longitude_coord.setValidator(coord_validator)
        
        self.add_field_to_layout(row_coords, "Latitude", latitude_coord)
        self.add_field_to_layout(row_coords, "Longitude", longitude_coord)
        container_layout.addLayout(row_coords)
        
        row_date = QHBoxLayout()
        now = datetime.now()
        current_y = now.year
        current_m = now.month

        # YEAR
        year_edit = QLineEdit(str(current_y))
        year_edit.setFixedWidth(60)
        year_edit.editingFinished.connect(lambda: self.fix_range(year_edit, current_y, current_y + 5))
        year_edit.setObjectName("year_input")
        self.add_field_to_layout(row_date, "Year", year_edit)
        
        # MONTH 
        month_edit = QLineEdit(str(current_m).zfill(2))
        month_edit.setFixedWidth(45)
        month_edit.editingFinished.connect(lambda: self.fix_range(month_edit, datetime.now().month, 12))
        month_edit.editingFinished.connect(lambda: self.fix_range(day_edit, 1, self.get_last_day(int(year_edit.text()), int(month_edit.text()))))
        month_edit.setObjectName("month_input")
        self.add_field_to_layout(row_date, "Month", month_edit)
        
        # DAY 
        last_day_in_month = self.get_last_day(int(year_edit.text()), int(month_edit.text()))
        target_day = now.day + 14
        if target_day > last_day_in_month:  target_day = last_day_in_month
        day_edit = QLineEdit(str(target_day).zfill(2))
        day_edit.setFixedWidth(45)
        day_edit.editingFinished.connect(lambda: self.fix_range(day_edit, now.day, self.get_last_day(int(year_edit.text()), int(month_edit.text()))))
        day_edit.setObjectName("day_input")
        self.add_field_to_layout(row_date, "Day", day_edit)
        
        utc_label = QLabel("UTC")
        utc_label.setFixedWidth(70)
        row_date.addWidget(utc_label)
        tz_edit = QLineEdit("-5")
        tz_edit.setFixedWidth(45)
        tz_edit.setObjectName("tz_input")
        self.add_field_to_layout(row_date, "TZ", tz_edit)
        
        self.handle_spaceport_combo(
            spaceport_combo, 
            latitude_coord, 
            longitude_coord, 
            tz_edit, 
            0
        )
        
        container_layout.addLayout(row_date)
        parent_layout.insertWidget(parent_layout.count() - 1, point_container)
        self.point_containers.append(point_container)

    def add_point(self):
        if self.points_count < 3:
            self.points_count += 1
            self.setup_input_ui(self.points_layout, self.points_count)
            if self.points_count >= 3: self.btn_add.hide()
    def remove_point(self, widget):
        widget.deleteLater()
        self.points_count -= 1
        if self.points_count < 3: self.btn_add.show()
        self.point_containers.pop(self.points_count)

    def show_loading(self):
        self.loading_window = AerooLoadingScreen()
        self.loading_window.show()
    def update_loading(self):
        pass
    def hide_loading(self):
        self.loading_window = AerooLoadingScreen()
        self.loading_window.hide()

    def show_analytics_window(self, path):
        self.analytics_window = AnalyticsWindow(path)
        self.analytics_window.show()

    def start_analyzing(self, btn):
        print("[A] ANALYZING STARTED!")
        btn.setEnabled(False)
        self.show_loading()
        
        mission_input = []
        
        print(f"Containers found: {len(self.point_containers)}")
        
        for container in self.point_containers:
            try:
                lat_w = container.findChild(QLineEdit, "lat_input")
                lon_w = container.findChild(QLineEdit, "lon_input")
                y_w = container.findChild(QLineEdit, "year_input")
                m_w = container.findChild(QLineEdit, "month_input")
                d_w = container.findChild(QLineEdit, "day_input")
                tz_w = container.findChild(QLineEdit, "tz_input")
                sp_w = container.findChild(QComboBox, "spaceport_input")

                if not all([lat_w, lon_w, y_w, m_w, d_w, tz_w, sp_w]):
                    print("[A] Error: Some widgets missing in this container. Operation aborted.")
                    break

                try:
                    lat_w_f = float(lat_w)
                    lon_w_f = float(lon_w)
                except:
                    print("[A] Error: Not all types are correct. Operation aborted.")
                    break
                else:
                    point_dict = {
                        "spaceport": sp_w.currentText(),
                        "coordinates": [float(lat_w.text()), float(lon_w.text())],
                        "target_timestamp": f"{y_w.text()}-{m_w.text().zfill(2)}-{d_w.text().zfill(2)}T00:00:00Z",
                        "timezone": f"UTC{tz_w.text()}"
                    }
                    mission_input.append(point_dict)
            except Exception as e: print(f"[A] Error during collection: {e}")

        print("Final collected data:", mission_input)
        
        # --- SENDING TO PROMPTER ---
        self.worker = AnalysisWorker(mission_input, prompter)
        self.worker.finished.connect(lambda f_name: self.on_analysis_finished(f_name, btn))
        self.worker.error.connect(lambda err: self.on_analysis_error(err, btn))
        self.worker.start()

    def on_analysis_finished(self, file_name, btn):
        try:
            current_analytics_path = os.path.join(REPORTS_PATH, file_name)
            print(f"Opening window for: {current_analytics_path}")
            self.show_analytics_window(current_analytics_path)
        except Exception as e: print(f"[A] Error showing window: {e}")
        self.finalize_ui(btn)
    def on_analysis_error(self, err, btn):
        print(f"[A] Analysis Thread Error: {err}")
        self.finalize_ui(btn)
    def finalize_ui(self, btn):
        self.hide_loading()
        btn.setEnabled(True)
        self.refresh_history()

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
        btn_analyse.clicked.connect(lambda: self.start_analyzing(btn_analyse))
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

        self.refresh_history()

        main_layout.addLayout(analytics_block, 1)
        main_layout.addLayout(right_container, 1)

if __name__ == "__main__":
    with open(STYLES, "r", encoding="utf-8") as f: STYLE_SHEET = f.read()
    app = QApplication(sys.argv)
    window = AerooSpaceApp()
    window.show()
    sys.exit(app.exec())