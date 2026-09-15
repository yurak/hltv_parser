"""Розвідка: чи проходить Selenium через Cloudflare на HLTV."""
import sys, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.hltv.org/results?team=9565"
headless = "--headed" not in sys.argv

opts = Options()
if headless:
    opts.add_argument("--headless=new")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--disable-gpu")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])

d = webdriver.Chrome(options=opts)
try:
    d.get(url)
    time.sleep(6)
    title = d.title
    html = d.page_source
    print("TITLE:", title)
    print("LEN:", len(html))
    low = html.lower()
    for marker in ["just a moment", "cf-challenge", "checking your browser",
                   "attention required", "enable javascript and cookies"]:
        if marker in low:
            print("BLOCKED-MARKER:", marker)
    # ознаки успіху
    for good in ["results-sublist", "result-con", "matchTicker", "team-box", "standard-headline"]:
        if good in html:
            print("OK-MARKER:", good)
    open("_probe_dump.html", "w").write(html)
    print("dump -> _probe_dump.html")
finally:
    d.quit()
