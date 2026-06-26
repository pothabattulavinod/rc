import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# ---------------- Files ----------------

INPUT_FILES = [
    "noutput10.json"
]

OUTPUT_FILE = "transactions.json"

BASE_URL = "https://aepos.ap.gov.in/smartepos/Qcodesearch.jsp?rcno={}"

# ---------------- Session ----------------

session = requests.Session()

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(
    max_retries=retry,
    pool_connections=20,
    pool_maxsize=20
)

session.mount("http://", adapter)
session.mount("https://", adapter)

session.headers.update({
    "User-Agent": "Mozilla/5.0 (GitHub Actions)"
})

# ---------------- Distribution Month ----------------

today = datetime.today()

if today.day >= 26:
    month = today.month + 1
    year = today.year
    if month == 13:
        month = 1
        year += 1
else:
    month = today.month
    year = today.year

month_name = datetime(year, month, 1).strftime("%B")

TARGET = f"{month_name}'{year} Transaction Details"

print("Checking:", TARGET)

# ---------------- Fetch ----------------

def fetch(card):
    cardno = card["CARDNO"]

    try:
        r = session.get(
            BASE_URL.format(cardno),
            timeout=20
        )
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        tables = soup.find_all("table")

        for table in tables:
            text = table.get_text(" ", strip=True)

            if TARGET not in text:
                continue

            rows = table.find_all("tr")

            for row in rows[3:]:
                cols = [
                    td.get_text(" ", strip=True)
                    for td in row.find_all("td")
                ]

                if len(cols) < 8:
                    continue

                try:
                    rice = float(cols[7])
                except:
                    continue

                units = int(card["UNITS"])
                expected = units * 5

                if rice == expected or rice == 35:
                    status = "Done"
                else:
                    status = "Not Done"

                return {
                    "CARDNO": card["CARDNO"],
                    "HEAD OF THE FAMILY": card["HEAD OF THE FAMILY"],
                    "UNITS": card["UNITS"],
                    "CURRENT_MONTH_TRANSACTION": {
                        "Member": cols[1],
                        "FPS": cols[2],
                        "Month": cols[3],
                        "Year": cols[4],
                        "Date": cols[5],
                        "Type": cols[6],
                        "Rice(KG)": rice,
                        "Expected(KG)": expected,
                        "Status": status
                    }
                }

        return {
            "CARDNO": card["CARDNO"],
            "HEAD OF THE FAMILY": card["HEAD OF THE FAMILY"],
            "UNITS": card["UNITS"],
            "CURRENT_MONTH_TRANSACTION": None
        }

    except requests.exceptions.RequestException as e:
        print(f"Request error: {cardno} -> {e}")
        time.sleep(1)
        return None

    except Exception as e:
        print(f"Unexpected error: {cardno} -> {e}")
        return None


# ---------------- Read Input ----------------

cards = []
order = {}
index = 0

for file in INPUT_FILES:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for card in data:
        cards.append(card)
        order[card["CARDNO"]] = index
        index += 1

print(f"Total cards loaded: {len(cards)}")

# ---------------- Process ----------------

results = []
failed = 0
success = 0

with ThreadPoolExecutor(max_workers=5) as executor:

    futures = {
        executor.submit(fetch, card): card
        for card in cards
    }

    total = len(futures)

    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()

        if result is None:
            failed += 1
        else:
            success += 1
            results.append(result)

        print(f"[{i}/{total}]")

# ---------------- Final Status ----------------

print(f"\nCompleted: {success} success, {failed} failed")

if success == 0:
    print("All requests failed. Server not reachable.")
    print(f"{OUTPUT_FILE} NOT modified.")
    raise SystemExit(1)

# ---------------- Restore Order ----------------

results.sort(key=lambda x: order[x["CARDNO"]])

# ---------------- Save Output ----------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"\n{OUTPUT_FILE} updated successfully.")
