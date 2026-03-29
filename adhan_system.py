import requests
from apscheduler.schedulers.blocking import BlockingScheduler
import pygame
import time

# Initialize audio
pygame.init()
pygame.mixer.init()

def play_adhan(prayer_name):
    print(f"Playing Adhan for {prayer_name}")
    pygame.mixer.music.load("adhan.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(1)

# Fetch prayer times
# Change method from MuslimWorldLeague to ISNA
url = "https://ummahapi.com/api/prayer-times?lat=29.7604&lng=-95.3698&madhab=Hanafi&method=ISNA&timezone=America/Chicago"

response = requests.get(url)
data = response.json()

timings = data["data"]["prayer_times"]
  # set to 1–2 minutes from now

# Create scheduler
scheduler = BlockingScheduler()

# Set your UTC offset (Houston is -5)
UTC_OFFSET = -5

# Schedule each prayer
for prayer, time_str in timings.items():
    if prayer.lower() in ["sunrise", "imsak", "midnight"]:
        continue

    hour, minute = map(int, time_str.split(":"))

    # ADJUST THE HOUR HERE
    local_hour = (hour + UTC_OFFSET) % 24

    scheduler.add_job(
        play_adhan,
        'cron',
        hour=local_hour,
        minute=minute,
        args=[prayer]
    )

    print(f"Scheduled {prayer} at {local_hour:02d}:{minute:02d}"
print("System running...")
print(data["data"]["location"])
scheduler.start()