import requests
from apscheduler.schedulers.blocking import BlockingScheduler
import pygame
import time

# --- CONFIGURATION ---
# If the API times are already correct for your local time, keep this at 0.
# If the times are off by a few hours, adjust this number (e.g., -5 or -6).
UTC_OFFSET = 0

# Initialize audio
pygame.init()
pygame.mixer.init()

def play_adhan(prayer_name):
    print(f"Playing Adhan for {prayer_name}")
    try:
        pygame.mixer.music.load("adhan.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(1)
    except Exception as e:
        print(f"Error playing audio: {e}")

# Fetch prayer times
# Location: Houston, TX | Method: ISNA | Madhab: Hanafi
url = "https://ummahapi.com/api/prayer-times?lat=29.7604&lng=-95.3698&madhab=Hanafi&method=ISNA&timezone=America/Chicago"

try:
    response = requests.get(url)
    response.raise_for_status() # Check for connection issues
    data = response.json()
    timings = data["data"]["prayer_times"]
except Exception as e:
    print(f"Failed to fetch prayer times: {e}")
    exit()

# Create scheduler
scheduler = BlockingScheduler()

print("--- Scheduled Prayer Times ---")

# Schedule each prayer
for prayer, time_str in timings.items():
    # Skip non-obligatory times
    if prayer.lower() in ["sunrise", "imsak", "midnight", "sunset", "ihtiyat"]:
        continue

    # Split "HH:MM" format
    hour, minute = map(int, time_str.split(":"))

    # Apply the UTC_OFFSET to fix the NameError
    local_hour = (hour + UTC_OFFSET) % 24

    # Adjust Asr prayer time if you prefer it one hour earlier
    # (Note: This might be redundant if you change the 'madhab' in the URL)
    if prayer.lower() == "asr":
        local_hour = (local_hour - 1) % 24

    scheduler.add_job(
        play_adhan,
        'cron',
        hour=local_hour,
        minute=minute,
        args=[prayer]
    )

    print(f"{prayer.capitalize():<10} | {local_hour:02d}:{minute:02d}")

print("-------------------------------")
print(f"Location: {data['data']['location']}")
print("System running... (Press Ctrl+C to stop)")

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    print("\nSystem stopped.")