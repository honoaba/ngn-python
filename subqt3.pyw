import sys
import time
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, 
                             QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QLabel, QListWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# -------------------------
# Worker Thread: بخش پردازش Selenium
# -------------------------
class SeleniumWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, numbers_list, username, password, login_url, target_url):
        super().__init__()
        self.numbers_list = numbers_list
        self.username = username
        self.password = password
        self.login_url = login_url
        self.target_url = target_url
        self.is_running = True

    def run(self):
        driver = None
        try:
            self.log_signal.emit("🚀 Starting Browser...")
            chrome_options = Options()
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 15)

            # Login
            driver.get(self.login_url)
            user_field = wait.until(EC.presence_of_element_located((By.ID, "login-form-login")))
            user_field.send_keys(self.username)
            pass_field = driver.find_element(By.ID, "login-form-password")
            pass_field.send_keys(self.password)
            login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary")))
            login_button.click()

            time.sleep(2)
            driver.get(self.target_url)

            failed_numbers = []
            for index, number in enumerate(self.numbers_list, start=1):
                if not self.is_running:
                    break

                try:
                    self.log_signal.emit(f"[{index}] Checking: {number}")
                    input_selector = "input[name='CallroutesSearch[dest_match]']"
                    input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, input_selector)))
                    
                    input_field.clear()
                    input_field.send_keys(str(number) + Keys.ENTER)
                    time.sleep(3)

                    if "No results found." in driver.find_element(By.TAG_NAME, "html").text:
                        self.log_signal.emit(f"❌ {number} Not Found")
                        failed_numbers.append(number)
                    else:
                        self.log_signal.emit(f"✅ {number} Exists")

                except Exception as e:
                    self.log_signal.emit(f"⚠️ Error on {number}")
                    failed_numbers.append(number)

            if failed_numbers:
                with open("e:/2/Not_Exist_Numbers.txt", "a") as f:
                    for fn in failed_numbers:
                        f.write(f"{fn}\n")
                self.log_signal.emit("📂 Failed numbers saved to txt.")

        except Exception as e:
            self.log_signal.emit(f"🔴 Critical Error: {str(e)}")
        finally:
            self.log_signal.emit("🏁 Process Finished.")
            self.finished_signal.emit()

    def stop(self):
        self.is_running = False

# -------------------------
# Main Window: رابط کاربری
# -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Call Route Checker Pro")
        self.resize(900, 600)
        self.input_file = ""
        self.numbers_list = []
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File Selection Row
        file_layout = QHBoxLayout()
        self.btn_browse = QPushButton("📁 Select Excel File")
        self.btn_browse.clicked.connect(self.browse_file)
        self.lbl_file = QLabel("No file selected")
        file_layout.addWidget(self.btn_browse)
        file_layout.addWidget(self.lbl_file)
        main_layout.addLayout(file_layout)

        # Middle Section (List + Log)
        content_layout = QHBoxLayout()
        
        # Left: Number List
        list_vbox = QVBoxLayout()
        list_vbox.addWidget(QLabel("Numbers Preview:"))
        self.list_widget = QListWidget()
        list_vbox.addWidget(self.list_widget)
        content_layout.addLayout(list_vbox, 1)

        # Right: Log Area
        log_vbox = QVBoxLayout()
        log_vbox.addWidget(QLabel("Console Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 11px;")
        log_vbox.addWidget(self.log_area)
        content_layout.addLayout(log_vbox, 2)

        main_layout.addLayout(content_layout)

        # Bottom: Buttons
        button_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 Start Process")
        self.btn_start.setFixedHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self.start_process)

        self.btn_stop = QPushButton("🛑 Stop")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_process)

        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_stop)
        main_layout.addLayout(button_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            self.input_file = file_path
            self.lbl_file.setText(file_path.split("/")[-1])
            self.preview_excel()

    def preview_excel(self):
        try:
            self.list_widget.clear()
            self.log_area.append("📖 Reading file...")
            df = pd.read_excel(self.input_file)
            if 'number' in df.columns:
                self.numbers_list = df['number'].astype(str).tolist()
                self.list_widget.addItems(self.numbers_list)
                self.log_area.append(f"✅ Loaded {len(self.numbers_list)} numbers.")
                self.btn_start.setEnabled(True)
            else:
                self.log_area.append("❌ Error: Column 'number' not found!")
                self.btn_start.setEnabled(False)
        except Exception as e:
            self.log_area.append(f"❌ Error: {str(e)}")

    def start_process(self):
        LOGIN_URL = "http://172.24.28.231:6060/web/index.php?r=user%2Fsecurity%2Flogin"
        TARGET_URL = "http://172.24.28.231:6060/web/index.php?r=call-routing%2Fshow-list&dev_id=11"
        USERNAME = "admin"
        PASSWORD = "nms.ava.97"

        self.log_area.clear()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker = SeleniumWorker(self.numbers_list, USERNAME, PASSWORD, LOGIN_URL, TARGET_URL)
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished_signal.connect(self.process_finished)
        self.worker.start()

    def stop_process(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.log_area.append("⚠️ Stopping...")
            self.btn_stop.setEnabled(False)

    def update_log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def process_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
