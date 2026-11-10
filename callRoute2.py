import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By


URL = "http://172.24.28.231:6060/web/index.php?r=call-routing%2Fcreate&dev_id=11"
EXCEL_FILE = "data.xlsx"


# ----------------------------
# تنظیم مقدار (برای input و select hidden)
# ----------------------------
def set_value(driver, element_id, value):
    el = driver.find_element(By.ID, element_id)

    driver.execute_script("arguments[0].value = arguments[1];", el, value)
    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
    """, el)


# ----------------------------
# کلیک امن (برای select2 ها اگر لازم شد)
# ----------------------------
def safe_click(driver, element_id):
    try:
        el = driver.find_element(By.ID, element_id)
        driver.execute_script("arguments[0].click();", el)
    except:
        pass


# ----------------------------
# اجرای اصلی
# ----------------------------
def main():

    df = pd.read_excel(EXCEL_FILE)

    driver = webdriver.Chrome()
    driver.maximize_window()

    print("شروع عملیات...")

    for i, row in df.iterrows():

        print("\n" + "="*50)
        print(f"➡️ رکورد شماره {i+1}")
        print("="*50)

        driver.get(URL)
        time.sleep(2)

        # ---------------- فرم ----------------
        set_value(driver, "order", str(row["order"]))
        set_value(driver, "dest_match", str(row["dest_match"]))

        set_value(driver, "location", "1")      # Incoming
        set_value(driver, "action", "Subscriber")

        set_value(driver, "param", "[P]")
        set_value(driver, "cr_cid", "[C]")

        # Home
        set_value(driver, "home_p", "1")
        set_value(driver, "home_s", "")

        # SoftSwitches
        set_value(driver, "dev_p_1", "11")
        set_value(driver, "dev_p_2", "13")
        set_value(driver, "dev_p_3", "17")
        set_value(driver, "dev_p_4", "18")

        time.sleep(1)

        # ---------------- Submit ----------------
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        print("✅ ارسال شد")

        # ---------------- کنترل کاربر ----------------
        while True:
            cmd = input("OK (Enter) / skip / exit : ").strip().lower()

            if cmd == "" or cmd == "ok":
                print("➡️ رفتن به رکورد بعدی")
                break

            elif cmd == "skip":
                print("⏭️ این رکورد رد شد")
                break

            elif cmd == "exit":
                print("❌ توقف برنامه")
                driver.quit()
                return

            else:
                print("دستور نامعتبر")

        time.sleep(1)

    driver.quit()
    print("تمام رکوردها انجام شد")


if __name__ == "__main__":
    main()