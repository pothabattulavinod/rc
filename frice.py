import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

# 1. Fetch JSON from GitHub
json_url = "https://raw.githubusercontent.com/pothabattulavinod/rcklv/refs/heads/main/sa.json"
try:
    response = requests.get(json_url, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"❌ Failed to fetch JSON from GitHub: {e}")
    exit(1)

output_file = "11sa.json"
total_rcs = len(data)

# 2. Detect current month
current_month = datetime.now().strftime("%B").lower()  # e.g., 'october'

# 3. Function to check a single RC for FRice availability
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
        if resp.status_code != 200:
            return {"CARDNO": rcno, "HEAD OF THE FAMILY": head_name, "transaction_status": "Unknown"}
    except requests.exceptions.RequestException:
        return {"CARDNO": rcno, "HEAD OF THE FAMILY": head_name, "transaction_status": "Unknown"}

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Combine all tables text
    tables_text = [
        table.get_text(separator='\n', strip=True) for table in soup.find_all('table')
    ]

    status = "Not Done"
    for table_text in tables_text:
        table_text_lower = table_text.lower()
        # Check if table is for current month and is a Transaction Details table
        if ("transaction details" in table_text_lower) and (re.search(current_month, table_text_lower, re.IGNORECASE)):
            # Check if FRice (KG) is present in this table
            if re.search(r'\bfrice\s*\(kg\)', table_text, re.IGNORECASE):
                status = "Done"
            break  # Stop after first matching month table

    return {"CARDNO": rcno, "HEAD OF THE FAMILY": head_name, "transaction_status": status}

# 4. Process RCs concurrently
transaction_data = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_rc, entry): entry.get('CARDNO') for entry in data}
    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        if result:
            transaction_data.append(result)
            print(f"Processed {i}/{total_rcs}: {result['CARDNO']} - {result['transaction_status']}")

# 5. Save results
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(transaction_data, f, indent=4, ensure_ascii=False)

print(f"✅ Processing complete. Results saved in '{output_file}'.")
