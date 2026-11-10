
import requests
import pandas as pd

BASE_URL = "http://172.24.28.231:6060/web/index.php"
LOGIN_URL = BASE_URL + "?r=user%2Fsecurity%2Flogin"

USERNAME = "admin"
PASSWORD = "nms.ava.97"

OUTPUT_FILE = "ngn_routes.html"

session = requests.Session()

def login():
    data = {
        "login-form-login": USERNAME,
        "login-form-password": PASSWORD
    }
    session.post(LOGIN_URL, data=data)

def fetch_routes():
    params = {
        "CallroutesSearch[order]": "",
        "CallroutesSearch[src_match]": "",
        "CallroutesSearch[dest_match]": "",
        "CallroutesSearch[min]": "",
        "CallroutesSearch[max]": "",
        "CallroutesSearch[action2]": "",
        "CallroutesSearch[location]": "",
        "CallroutesSearch[param]": "",
        "CallroutesSearch[comments]": "",
        "r": "call-routing/show-list",
        "dev_id": "11",
        "pageSize": "1000"
    }

    r = session.get(BASE_URL, params=params)
    return r.text

def main():
    login()
    html = fetch_routes()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print("DONE ->", OUTPUT_FILE)

if __name__ == "__main__":
    main()
