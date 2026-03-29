import requests

url = "https://www.islamicfinder.org/world/united-states/4699066/houston-prayer-times/#google_vignette"  # temporary test site
response = requests.get(url)

print(response.status_code)
print(response.text[:200])