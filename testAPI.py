import requests

url = "https://ummahapi.com/api/prayer-times?lat=24.8607&lng=67.0011&madhab=Hanafi&method=MuslimWorldLeague"

try:
    response = requests.get(url)
    response.raise_for_status()  # Check for HTTP errors
    data = response.json()

    # Safely access the data
    if "data" in data and "timings" in data["data"]:
        timings = data["data"]["timings"]

        print("Fajr:", timings.get("Fajr"))
        print("Dhuhr:", timings.get("Dhuhr"))
        print("Asr:", timings.get("Asr"))
        print("Maghrib:", timings.get("Maghrib"))
        print("Isha:", timings.get("Isha"))
    else:
        print("Error: Unexpected API response structure.")
        print("Response:", data)

except requests.exceptions.RequestException as e:
    print(f"Error fetching prayer times: {e}")
except ValueError:
    print("Error: Could not parse JSON response.")
