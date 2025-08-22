# parser.py
import os
import csv
import time
import pathlib
import traceback
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait as W
from selenium.webdriver.support import expected_conditions as EC

# твої модулі
from selenium_data_builder import SeleniumDataBuiler
from clusterization.role_features import CS_MAPS, PLAYERS_TOP20_SOURCE


# -------------------- утиліти дебагу --------------------
ART_DIR = pathlib.Path("artifacts")
ART_DIR.mkdir(exist_ok=True)

def dump_artifacts(driver, tag="step"):
    """Зберегти скріншот і HTML сторінки для дебагу."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    png = ART_DIR / f"{ts}_{tag}.png"
    html = ART_DIR / f"{ts}_{tag}.html"
    try:
        driver.save_screenshot(str(png))
    except Exception:
        pass
    try:
        html.write_text(driver.page_source or "", encoding="utf-8")
    except Exception:
        pass
    print(f"[ART] saved {png.name}, {html.name}")

def print_browser_logs(driver):
    """Вивести логи консолі браузера."""
    try:
        for e in driver.get_log("browser"):
            lvl = e.get("level")
            msg = e.get("message")
            print(f"[BROWSER] {lvl}: {msg}")
    except Exception:
        # не всі білди підтримують логи — це ок
        pass

def wait_css(driver, css, to=15):
    """Дочекатися елемента за CSS-селектором."""
    return W(driver, to).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))

def with_retries(fn, tries=3, delay=1.0, tag="op"):
    """Проста обгортка для повторних спроб."""
    last_err = None
    for i in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            print(f"[RETRY {i}/{tries}] {tag}: {e}")
            time.sleep(delay)
    if last_err:
        raise last_err


# -------------------- основний клас --------------------
class SeleniumParser:
    BASE_URL = "https://www.hltv.org/stats/players/"

    def __init__(self, filename, player_sufix, cs_map, headless=None, debug=None):
        self.filename = filename
        self.data_dict = {}
        self.player_sufix = player_sufix
        self.cs_map = cs_map

        # Перемикачі через ENV (HEADLESS=0 щоб побачити браузер, DEBUG=1 щоб зберігати артефакти)
        if headless is None:
            self.headless = os.getenv("HEADLESS", "1") != "0"
        else:
            self.headless = headless

        if debug is None:
            self.debug = os.getenv("DEBUG", "0") == "1"
        else:
            self.debug = debug

        if not os.path.exists(self.filename):
            self._create_file()

        self._driver = None
        if self._needs_driver():
            self._driver = self._build_driver()

    # ---------- infra ----------
    def _build_driver(self):
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        else:
            # зручно для дебагу: одразу DevTools
            opts.add_argument("--auto-open-devtools-for-tabs")

        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--remote-debugging-port=0")
        opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        # Використовуємо Selenium Manager (не треба webdriver-manager)
        # За можливості пишемо лог chromedriver (підтримується в selenium>=4.24)
        service = None
        try:
            service = Service(log_output="chromedriver.log")
        except TypeError:
            service = Service()  # старіші версії без log_output

        driver = webdriver.Chrome(service=service, options=opts)
        return driver

    def _create_file(self):
        with open(self.filename, "w"):
            pass

    def _df(self):
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0:
            return pd.DataFrame()
        try:
            return pd.read_csv(self.filename)
        except Exception:
            return pd.DataFrame()

    def _needs_driver(self):
        df = self._df()
        return df.empty or self.full_url() not in df.get("full_url", pd.Series([])).values

    def close(self):
        if self._driver:
            try:
                self._driver.quit()
            finally:
                self._driver = None

    # ---------- scraping ----------
    def full_url(self):
        return f"{self.BASE_URL}{self.player_sufix}?maps={self.cs_map}"

    def _hltv_response(self):
        # Навігація + коректне очікування
        self._driver.get(self.full_url())
        # Спробуємо дочекатися нікнейм (коли є), інакше — просто <body>
        try:
            wait_css(self._driver, "h1.summaryNickname, body", to=15)
        except Exception:
            pass

    def data_from_response(self):
        self.data_dict = {}

        def do_load():
            self._hltv_response()
            if self.debug:
                dump_artifacts(self._driver, "after_load")

        with_retries(do_load, tries=3, delay=1.0, tag="load")

        try:
            builder = SeleniumDataBuiler(self._driver, self.cs_map)
            self.data_dict["full_url"] = self.full_url()
            # '922/snappi' -> беремо частину після слеша
            self.data_dict["player_name"] = self.player_sufix.split("/")[1]
            built = builder.build()
            self.data_dict.update(built)
        except Exception as e:
            if self.debug:
                dump_artifacts(self._driver, "error")
                print_browser_logs(self._driver)
            print(f"[ERR] {self.full_url()} -> {e}")
            # Додатково — стек у лог
            traceback.print_exc()
        else:
            if self.debug:
                print_browser_logs(self._driver)

        return self.data_dict

    # ---------- IO ----------
    def write_file(self, only_headers=True):
        with open(self.filename, "a+", newline="") as file:
            writer = csv.writer(file)
            if only_headers:
                if self.data_dict:
                    writer.writerow(self.data_dict.keys())
            else:
                if self.data_dict:
                    print(f"[OK] {self.player_sufix} on {self.cs_map}")
                    writer.writerow(self.data_dict.values())
                else:
                    print(f"[MISS] Data not found: {self.player_sufix}")

    def write_headers(self):
        if os.path.getsize(self.filename) == 0:
            print("[HDR] writing headers…")
            self.data_from_response()
            self.write_file(only_headers=True)
            self.close()

    # ---------- public API ----------
    def parse(self, only_headers=False):
        if self.full_url() not in self._df().get("full_url", pd.Series([])).values:
            self.data_from_response()
            self.write_file(only_headers=False if not only_headers else True)
            self.close()

    # ---------- batches ----------
    @classmethod
    def run_all_maps(cls):
        file_name = "hltv_attributes_selenium_top20_allmapsv2_hltv3_0.csv"
        cls(file_name, "922/snappi", "de_nuke").write_headers()
        with open(PLAYERS_TOP20_SOURCE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                time.sleep(0.1)
                cls(file_name, row[0], "all").parse()

    @classmethod
    def run_competetive_maps(cls):
        file_name = "hltv_attributes_selenium_top20_competetive_maps_hltv3_0.csv"
        cls(file_name, "922/snappi", "de_nuke").write_headers()
        with open(PLAYERS_TOP20_SOURCE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                for cs_map in CS_MAPS:
                    time.sleep(0.1)
                    cls(file_name, row[0], cs_map).parse()


if __name__ == "__main__":
    # Обери потрібний ран:
    SeleniumParser.run_all_maps()
    # SeleniumParser.run_competetive_maps()
