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

    # Date ranges for game versions (CS2 launched Sep 27, 2023)
    GAME_DATES = {
        "cs2": {"startDate": "2023-09-27", "endDate": "2025-12-31"},
        "csgo": {"startDate": "2012-08-21", "endDate": "2023-09-26"},
        "all": {}  # no date filter
    }

    def __init__(self, filename, player_sufix, cs_map, game_version="cs2", headless=None, debug=None):
        self.filename = filename
        self.data_dict = {}
        self.player_sufix = player_sufix
        self.cs_map = cs_map
        self.game_version = game_version.lower()

        if self.game_version not in self.GAME_DATES:
            raise ValueError(f"game_version must be one of {list(self.GAME_DATES.keys())}, got '{game_version}'")

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

        # Window and display settings
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--start-maximized")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        # Enable JavaScript and disable GPU issues
        opts.add_argument("--enable-javascript")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")

        # User agent to avoid bot detection
        opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Additional options for better compatibility
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

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
        url = f"{self.BASE_URL}{self.player_sufix}?maps={self.cs_map}"

        # Add date filters for game version
        date_params = self.GAME_DATES[self.game_version]
        if date_params:
            url += f"&startDate={date_params['startDate']}&endDate={date_params['endDate']}"

        return url

    def _hltv_response(self):
        # Навігація + коректне очікування
        self._driver.get(self.full_url())

        # Спробуємо дочекатися нікнейм (коли є), інакше — просто <body>
        try:
            wait_css(self._driver, "h1.summaryNickname, body", to=10)
        except Exception:
            pass

        # Wait for dynamic content to load (optimized)
        time.sleep(0.8)

    def data_from_response(self):
        self.data_dict = {}

        def do_load():
            self._hltv_response()
            if self.debug:
                dump_artifacts(self._driver, "after_load")

        with_retries(do_load, tries=2, delay=0.5, tag="load")

        try:
            builder = SeleniumDataBuiler(self._driver, self.cs_map)
            self.data_dict["full_url"] = self.full_url()
            # '922/snappi' -> беремо частину після слеша
            self.data_dict["player_name"] = self.player_sufix.split("/")[1]
            self.data_dict["game_version"] = self.game_version
            built = builder.build()
            self.data_dict.update(built)
        except Exception as e:
            if self.debug:
                dump_artifacts(self._driver, "error")
                print_browser_logs(self._driver)
                traceback.print_exc()
            else:
                print(f"[ERR] {self.player_sufix}: {e}")
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
                if self.data_dict and len(self.data_dict) > 5:  # Should have more than just basic fields
                    print(f"[OK] {self.player_sufix} on {self.cs_map} ({len(self.data_dict)} fields)")
                    writer.writerow(self.data_dict.values())
                elif self.data_dict:
                    print(f"[WARN] Incomplete data for {self.player_sufix}: only {len(self.data_dict)} fields")
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
    def run_all_maps(cls, game_version="cs2"):
        """Scrape all maps data for specified game version (cs2, csgo, or all)."""
        file_name = f"hltv_attributes_selenium_top20_allmapsv2_{game_version}.csv"
        cls(file_name, "922/snappi", "de_nuke", game_version=game_version).write_headers()
        with open(PLAYERS_TOP20_SOURCE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                # No sleep needed - reduced from 0.1s
                cls(file_name, row[0], "all", game_version=game_version).parse()

    @classmethod
    def run_competetive_maps(cls, game_version="cs2"):
        """Scrape competitive maps data for specified game version (cs2, csgo, or all)."""
        file_name = f"competetive_maps_{game_version}.csv"
        cls(file_name, "922/snappi", "de_nuke", game_version=game_version).write_headers()
        with open(PLAYERS_TOP20_SOURCE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                for cs_map in CS_MAPS:
                    # No sleep needed - reduced from 0.1s
                    cls(file_name, row[0], cs_map, game_version=game_version).parse()

    @classmethod
    def run_all_maps_both_games(cls):
        """Scrape all maps data for both CS2 and CS:GO."""
        print("\n=== Starting CS2 data collection ===")
        cls.run_all_maps(game_version="cs2")
        print("\n=== Starting CS:GO data collection ===")
        cls.run_all_maps(game_version="csgo")

    @classmethod
    def run_competetive_maps_both_games(cls):
        """Scrape competitive maps data for both CS2 and CS:GO."""
        print("\n=== Starting CS2 data collection ===")
        cls.run_competetive_maps(game_version="cs2")
        print("\n=== Starting CS:GO data collection ===")
        cls.run_competetive_maps(game_version="csgo")


if __name__ == "__main__":
    # Running for both CS2 and CS:GO
    print("Starting data collection for CS2 and CS:GO...")
    print(f"Total players to process: 183")
    print("=" * 60)

    SeleniumParser.run_all_maps_both_games()
    SeleniumParser.run_competetive_maps_both_games()

    print("=" * 60)
    print("Data collection completed!")
    print("Output files:")
    print("  - hltv_attributes_selenium_top20_allmapsv2_cs2.csv")
    print("  - hltv_attributes_selenium_top20_allmapsv2_csgo.csv")
    print("  - competetive_maps_cs2.csv")
    print("  - competetive_maps_csgo.csv")
