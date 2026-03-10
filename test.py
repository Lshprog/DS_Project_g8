import requests

url = "https://www.businesstimes.com.sg/companies-markets/energy-commodities/gold-gains-traders-mull-next-trump-moves-after-tariff-ruling"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
    "Accept-Language": "en-SG,en;q=0.9",
}

r = requests.get(url, headers=headers, timeout=30)
r.raise_for_status()

with open("debug_requests_html.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved debug_requests_html.html (open it in your browser)")
print("Length:", len(r.text))