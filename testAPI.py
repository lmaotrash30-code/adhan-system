import requests

url = "https://ummahapi.com/api/prayer-times?lat=29.7604&lng=-95.3698&madhab=Hanafi&method=MuslimWorldLeague&timezone=America/Chicago"

try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # Correct structure
    if "data" in data and "prayer_times" in data["data"]:
        timings = data["data"]["prayer_times"]

        print("Fajr:", timings.get("fajr"))
        print("Dhuhr:", timings.get("dhuhr"))
        print("Asr:", timings.get("asr"))
        print("Maghrib:", timings.get("maghrib"))
        print("Isha:", timings.get("isha"))
    else:
        print("Error: Unexpected API response structure.")
        print("Response:", data)

except requests.exceptions.RequestException as e:
    print(f"Error fetching prayer times: {e}")
except ValueError:
    print("Error: Could not parse JSON response.")