import requests
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ======= 1. RC Numbers List =======
rc_numbers = ["2822185062", "2820444126", "2805306208"]

# ======= 2. Setup headers and month =======
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )
}
current_month = datetime.now().strftime("%B").lower()  # e.g., 'october'

# ======= 3. Function to fetch and print current month Transaction Details =======
def fetch_transaction_table(rcno):
    url = f'https://aepos.ap.gov.in/Qcodesearch.jsp?rcno={rcno}'
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ RC {rcno}: Failed to fetch page ({e})")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    tables = soup.find_all('table')

    found_table = None
    for table in tables:
        table_text = table.get_text(separator=' ', strip=True).lower()
        if "transaction details" in table_text and re.search(current_month, table_text, re.IGNORECASE):
            found_table = table
            break

    if found_table:
        print(f"\n===== 🗓️ {current_month.capitalize()} Transaction Details for RC: {rcno} =====\n")
        print(found_table.get_text(separator='\n', strip=True))
    else:
        print(f"\n⚠️ RC {rcno}: No '{current_month.capitalize()} Transaction Details' table found")

# ======= 4. Run concurrently for all RCs =======
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(fetch_transaction_table, rcno) for rcno in rc_numbers]
    for future in as_completed(futures):
        future.result()

print("\n✅ Completed fetching Transaction Details for all RCs.")
