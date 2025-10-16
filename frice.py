import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

# =====================================================
# 1. Fetch JSON from GitHub
# =====================================================
json_url = "https://raw.githubusercontent.com/pothabattulavinod/rcklv/refs/heads/main/sa.json"  # <-- Replace if needed

try:
    response = requests.get(json_url, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"❌ Failed to fetch JSON from GitHub: {e}")
    exit(1)

output_file = "11sa.json"
total_rcs = len(data)

# =====================================================
# 2. Detect current month (e.g., 'october')
# =====================================================
current_month = datetime.now().strftime("%B").lower()
short_month = current_month[:3]

# =====================================================
# 3. Function to check a single RC
# =====================================================
def check_rc(rc_entry):
    rcno = rc_entry.get('CARDNO')
    head_name = rc_entry.get('HEAD OF THE FAMILY', 'Unknown')
    if not rcno:
        return None

    url = f'https://aepos.ap.gov.in/Qcodesearch.jsp?rcno={rcno}'
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.1 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return {
            "CARDNO": rcno,
            "HEAD OF THE FAMILY": head_name,
            "transaction_status": "Unknown",
            "found_items": {}
        }

    soup = BeautifulSoup(resp.text, 'html.parser')
    tables_text = " ".join(
        [table.get_text(separator='\n', strip=True).lower() for table in soup.find_all('table')]
    )

    # =====================================================
    # 3.1 Extract only current month’s section
    # =====================================================
    month_sections = re.findall(
        rf"({current_month}[\s\S]*?)(?=(january|february|march|april|may|june|july|august|september|october|november|december|$))",
        tables_text,
        re.IGNORECASE
    )
    month_text = month_sections[0][0] if month_sections else ""

    # =====================================================
    # 3.2 Detect commodities for current month
    # =====================================================
    rice_found = bool(re.search(r'\bfrice\s*\(kg\)', month_text, re.IGNORECASE))
    sugar_found = bool(re.search(r'sugar', month_text, re.IGNORECASE))

    # =====================================================
    # 3.3 Determine transaction status
    # =====================================================
    if rice_found:
        status = "Done"
    else:
        status = "Not Done"

    return {
        "CARDNO": rcno,
        "HEAD OF THE FAMILY": head_name,
        "transaction_status": status,
        "found_items": {
            "rice": rice_found,
            "sugar": sugar_found
        }
    }

# =====================================================
# 4. Process RCs concurrently
# =====================================================
transaction_data = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_rc, entry): entry.get('CARDNO') for entry in data}
    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        if result:
            transaction_data.append(result)
            print(f"Processed {i}/{total_rcs}: {result['CARDNO']} - {result['transaction_status']}")

# =====================================================
# 5. Save results to JSON
# =====================================================
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(transaction_data, f, indent=4, ensure_ascii=False)

print(f"✅ Processing complete. Results saved in '{output_file}'.")
