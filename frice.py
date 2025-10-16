import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# ======= 1. Input RC number =======
rcno = "2820444126"  # <-- change if needed

# ======= 2. Setup URL and headers =======
url = f'https://aepos.ap.gov.in/Qcodesearch.jsp?rcno={rcno}'
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )
}

# ======= 3. Fetch the page =======
try:
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"❌ Failed to fetch RC {rcno}: {e}")
    exit(1)

# ======= 4. Parse HTML =======
soup = BeautifulSoup(resp.text, 'html.parser')
tables_text = " ".join([
    table.get_text(separator='\n', strip=True).lower()
    for table in soup.find_all('table')
])

# ======= 5. Extract current month section =======
current_month = datetime.now().strftime("%B").lower()
month_sections = re.findall(
    rf"({current_month}[\s\S]*?)(?=(january|february|march|april|may|june|july|august|september|october|november|december|$))",
    tables_text,
    re.IGNORECASE
)

if month_sections:
    month_text = month_sections[0][0]
    print(f"\n===== 🗓️ {current_month.capitalize()} Data for RC: {rcno} =====\n")
    print(month_text)
else:
    print(f"\n⚠️ No data found for {current_month.capitalize()} in RC: {rcno}")
