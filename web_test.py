import requests
from bs4 import BeautifulSoup

url = "https://iec-houston.org/prayer-times/"  # replace with your real URL

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

tables = soup.find_all("table")
target_table = tables[1]

rows = target_table.find_all("tr")

for i, row in enumerate(rows):
    columns = row.find_all(["td", "th"])
    values = [col.get_text(strip=True) for col in columns]

    print(f"Row {i}: {values}")