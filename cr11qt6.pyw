import sys
import time
import pandas as pd
import os
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, 
    QTextEdit, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# تنظیمات ثابت
URL = "http://172.24.28.231:6060/web/index.php?r=call-routing%2Fcreate&dev_id=11"
LOGIN_URL = "http://172.24.28.231:6060/web/index.php?r=user%2Fsecurity%2Flogin"
USERNAME = "admin"
PASSWORD = "nms.ava.97"

class Worker(QThread):
    log = pyqtSignal(str)
    row_completed = pyqtSignal(int)
    finished_signal = pyqtSignal()
    
    def __init__(self, excel_path, mapping):
        super().__init__()
        self.excel_path = excel_path
        self.mapc = mapping
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        df = pd.read_excel(self.excel_path)
        
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")

        service = Service(log_output=os.devnull)
        service.creation_flags = subprocess.CREATE_NO_WINDOW
        
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            self.log.emit(f"Driver Error: {str(e)}")
            return

        wait = WebDriverWait(driver, 15)

        try:
            self.log.emit("🔐 Logging in...")
            driver.get(LOGIN_URL)
            user_field = wait.until(EC.presence_of_element_located((By.ID, "login-form-login")))
            user_field.send_keys(USERNAME)
            driver.find_element(By.ID, "login-form-password").send_keys(PASSWORD)
            driver.find_element(By.CSS_SELECTOR, "button.btn-primary").click()
            time.sleep(2)
        except Exception as e:
            self.log.emit(f"Login issue: {e}")

        for i, row in df.iterrows():
            if not self._is_running:
                self.log.emit("🛑 Process stopped by user.")
                break

            # استخراج مقدار شماره برای لاگ
            order_val = str(row.get(self.mapc.get('order'), i+1))
            dest_match  = str(row.get(self.mapc.get('dest_match')))
            self.log.emit(f"🔄 Processing [{dest_match}]")
            #self.log.emit(f"🔄 Processing [{order_val}]")
            
            try:
                driver.get(URL)
                time.sleep(2)
                
                def set_input(d, el_id, val):
                    try:
                        el = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, el_id)))
                        el.clear()
                        el.send_keys(str(val))
                    except: pass

                def set_select(d, el_id, val):
                    try:
                        d.execute_script("let el=document.getElementById(arguments[0]); if(el){el.value=arguments[1]; el.dispatchEvent(new Event('change',{bubbles:true}));}", el_id, val)
                    except: pass

                set_input(driver, "order", row.get(self.mapc["order"], ""))
                set_select(driver, "location", row.get(self.mapc["location"], ""))
                set_input(driver, "dest_match", row.get(self.mapc["dest_match"], ""))
                set_select(driver, "action", row.get(self.mapc["action"], ""))

                primary = row.get(self.mapc["home_p"], "")
                if primary != "" and str(primary).lower() != "nan":
                    set_select(driver, "home_p", primary)
                    for k in ["dev_p_1", "dev_p_2", "dev_p_3", "dev_p_4"]:
                        set_select(driver, "dev_p_" + k.split("_")[1], row.get(self.mapc[k], ""))
                    set_select(driver, "home_s", "")
                else:
                    set_select(driver, "home_s", row.get(self.mapc["home_s"], ""))

                driver.find_element(By.XPATH, "//input[@type='submit']").click()
                
                time.sleep(2)
                self.row_completed.emit(i) 
                
            except Exception as e:
                self.log.emit(f"❌ Error in row {i+1}: {str(e)}")

        self.log.emit("✅ All tasks finished.")
        self.finished_signal.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.mapping = {}
        self.current_excel_path = ""
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Create Call Route App")
        self.resize(900, 600)
        
        main_layout = QVBoxLayout()

        # --- Top Controls ---
        top_control_layout = QHBoxLayout()
        self.btn_file = QPushButton("📂 Select Excel")
        self.btn_start = QPushButton("▶ Start")
        self.btn_stop = QPushButton("⏹ Stop")
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        #self.btn_stop.setStyleSheet("background-color: #eeff22; color: white; font-weight: bold;")
        self.btn_start.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")

        top_control_layout.addWidget(self.btn_file)
        top_control_layout.addWidget(self.btn_start)
        top_control_layout.addWidget(self.btn_stop)
        main_layout.addLayout(top_control_layout)

        # --- Body: Table (Left) and Log (Right) ---
        body_layout = QHBoxLayout()

        # Table Container (Left Side)
        table_container = QVBoxLayout()
        table_label = QLabel("<b></b>")
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        #self.table.setFixedWidth(220) # عرض ثابت و کم برای ستون شماره/مقدار
        self.table.setFixedWidth(150) # عرض ثابت و کم برای ستون شماره/مقدار
        self.table.setHorizontalHeaderLabels(["NUMBERS"])
        self.table.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
        background-color: #f0f0f0;
        padding: 4px;
        font-weight: bold; 
        
        
        }
        """)
         #border: 1px solid #dcdde1;
        #font-size: 13px;




        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        table_container.addWidget(table_label)
        table_container.addWidget(self.table)
        
        # Log Container (Right Side)
        log_container = QVBoxLayout()
        log_label = QLabel("<b>Execution Logs</b>")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; font-family: Consolas; font-size: 11px;")
        
        log_container.addWidget(log_label)
        log_container.addWidget(self.log_output)

        # Add both to body
        body_layout.addLayout(table_container)
        body_layout.addLayout(log_container)
        
        main_layout.addLayout(body_layout)
        self.setLayout(main_layout)

        # Connections
        self.btn_file.clicked.connect(self.load_excel)
        self.btn_start.clicked.connect(self.start_process)
        self.btn_stop.clicked.connect(self.stop_process)

        self.setStyleSheet("""
            QWidget { font-size: 13px; background-color: #fdfdfd; }
            QPushButton { padding: 8px 15px; border-radius: 4px; font-weight: bold; }
            QTableWidget { border: 1px solid #dcdde1; background-color: white; }
        """)

    def load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx)")
        if path:
            self.current_excel_path = path
            try:
                self.df = pd.read_excel(path)
                self.df.columns = self.df.columns.astype(str).str.strip()
                self.prepare_mapping()
                self.display_dest_match_only()
                self.btn_start.setEnabled(True)
                self.log_output.append(f"✅ File Ready: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def display_dest_match_only(self):
        """فقط ستون dest_match و شماره ردیف را در قالب ترکیبی نشان می‌دهد"""
        self.table.setRowCount(len(self.df))
        
        dest_col = self.mapping.get("dest_match")
        order_col = self.mapping.get("order")
        
        for i in range(len(self.df)):
            # استخراج مقدار شماره
            idx_val = str(self.df.iloc[i][order_col]) if order_col and order_col in self.df.columns else str(i+1)
            # استخراج مقدار dest_match
            dest_val = str(self.df.iloc[i][dest_col]) if dest_col and dest_col in self.df.columns else "N/A"
            
            # ترکیب در یک رشته برای نمایش در یک ستون باریک
            #combined_text = f"{idx_val} | {dest_val}"
            combined_text = f"{dest_val}"
            item = QTableWidgetItem(combined_text)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item)

    def prepare_mapping(self):
        def find_col(names):
            cols = {c.lower().strip(): c for c in self.df.columns}
            for n in names:
                if n.lower() in cols: return cols[n.lower()]
            return None

        self.mapping = {
            "order": find_col(["order", "شماره", "id"]),
            "location": find_col(["location"]),
            "dest_match": find_col(["dest_match"]),
            "action": find_col(["action"]),
            "home_p": find_col(["home_p", "dual_home_p"]),
            "home_s": find_col(["home_s"]),
            "dev_p_1": find_col(["dev_p_1"]),
            "dev_p_2": find_col(["dev_p_2"]),
            "dev_p_3": find_col(["dev_p_3"]),
            "dev_p_4": find_col(["dev_p_4"]),
        }

    def start_process(self):
        self.btn_start.setEnabled(False)
        self.btn_file.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        self.worker = Worker(self.current_excel_path, self.mapping)
        self.worker.log.connect(self.update_log)
        self.worker.row_completed.connect(self.highlight_row_soft)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def stop_process(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.btn_stop.setEnabled(False)

    def update_log(self, msg):
        self.log_output.append(msg)

    def highlight_row_soft(self, row_idx):
        """تغییر رنگ به سبز ملایم"""
        for j in range(self.table.columnCount()):
            item = self.table.item(row_idx, j)
            if item:
                item.setBackground(QColor("#C8E6C9")) 
                item.setForeground(QColor("#2E7D32"))

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_file.setEnabled(True)
        self.btn_stop.setEnabled(False)
        QMessageBox.information(self, "Status", "Process finished.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
