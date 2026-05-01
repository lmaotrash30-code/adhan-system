# 🕌 Adhan System — Raspberry Pi

An automated Islamic prayer time (Adhan) player for Raspberry Pi. Fetches accurate daily prayer times for **Sugar Land, TX** via the [Aladhan API](https://aladhan.com/prayer-times-api), plays the correct Adhan audio for each prayer, and recovers automatically from WiFi disconnections.

---

## Features

- Plays Adhan automatically at all 5 daily prayer times
- Separate audio pool for Fajr — randomly picks from multiple recordings each time
- Separate audio pool for all other prayers — also randomly picked
- Fetches fresh prayer times daily from the Aladhan API (ISNA method, Hanafi school)
- Startup catch-up — if the script restarts within 10 minutes of a prayer, it plays immediately
- Hard kill after 15 minutes to ensure no audio process hangs
- Full logging to `adhan.log`
- WiFi watchdog — automatically reconnects if internet is lost

---

## Repository Structure

```
adhan-system/
├── adhan_system.py        # Main prayer scheduler script
├── wifi_watchdog.sh       # WiFi reconnection watchdog script
├── fajr/                  # Fajr-specific audio files go here
│   ├── adhan_fajr_1.mp3
│   └── adhan_fajr_2.mp3
├── standard/              # All other prayers audio files go here
│   ├── adhan_1.mp3
│   └── adhan_2.mp3
├── adhan.mp3              # Fallback audio if pools are empty
└── README.md
```



## Requirements

> ⚠️ All dependencies must be installed **directly on the Raspberry Pi**, not on your local machine.

### System Packages
Run these commands on the Pi terminal:
```bash
sudo apt update
sudo apt install ffmpeg python3-pip
```
`ffmpeg` provides `ffplay` which handles all audio playback.

### Python Packages
Run this on the Pi terminal:
```bash
pip3 install requests apscheduler --break-system-packages
```

### Verify Everything Is Installed
```bash
ffplay -version
python3 -c "import requests, apscheduler; print('All good')"
```

---

## Installation

### 1. Clone the repository onto the Pi
```bash
cd /home/ozen
git clone git@github.com:yourusername/adhan-system.git
cd adhan-system
```

### 2. Create the audio folders if they don't exist
```bash
mkdir -p fajr standard
```

### 3. Add your audio files
Copy your `.mp3` files into the correct folders on the Pi:
- Fajr recordings → `/home/ozen/adhan-system/fajr/`
- All other prayers → `/home/ozen/adhan-system/standard/`
- Fallback file → `/home/ozen/adhan-system/adhan.mp3`

If your files are `.mp4`, convert them to `.mp3` first (one-time only):
```bash
# Convert a single file
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3

# Convert all MP4s in the fajr folder at once
for f in /home/ozen/adhan-system/fajr/*.mp4; do ffmpeg -i "$f" -q:a 0 -map a "${f%.mp4}.mp3"; done

# Convert all MP4s in the standard folder at once
for f in /home/ozen/adhan-system/standard/*.mp4; do ffmpeg -i "$f" -q:a 0 -map a "${f%.mp4}.mp3"; done
```

---

## Running the Adhan System

```bash
python3 /home/ozen/adhan-system/adhan_system.py
```

To verify audio output is working at any time:
```bash
ffplay -nodisp -autoexit -loglevel quiet -f lavfi "sine=frequency=1000:duration=1"
```
A 1-second beep confirms ffplay and your audio output are working.

---

## Autostart on Boot

To have the adhan system start automatically every time the Pi powers on, set it up as a systemd service.

> ⚠️ The following commands are run **on the Raspberry Pi terminal**, not on your local machine.

**1. Create the service file:**
```bash
sudo nano /etc/systemd/system/adhan.service
```

**2. Paste the following:**
```ini
[Unit]
Description=Adhan Prayer System
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/ozen/adhan-system/adhan_system.py
WorkingDirectory=/home/ozen/adhan-system
Restart=always
RestartSec=10
User=ozen

[Install]
WantedBy=multi-user.target
```

**3. Enable and start it:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable adhan
sudo systemctl start adhan
```

**4. Check it's running:**
```bash
sudo systemctl status adhan
```

**5. View live logs:**
```bash
tail -f /home/ozen/adhan-system/adhan.log
```

---

## WiFi Watchdog

The WiFi watchdog is a separate script that runs alongside the adhan system. It pings Google's DNS (`8.8.8.8`) every 30 seconds and automatically reconnects if the Pi loses its WiFi connection.

**Reconnect escalation order:**
1. `wpa_cli reassociate` — tried up to 5 times
2. Interface bounce (`ip link down/up`)
3. `dhcpcd` service restart
4. If all fail — keeps retrying every 30 seconds indefinitely

> ⚠️ The following commands are run **on the Raspberry Pi terminal**, not on your local machine.

**1. Make the script executable:**
```bash
chmod +x /home/ozen/adhan-system/wifi_watchdog.sh
```

**2. Create the service file:**
```bash
sudo nano /etc/systemd/system/wifi-watchdog.service
```

**3. Paste the following:**
```ini
[Unit]
Description=WiFi Watchdog
After=network.target

[Service]
ExecStart=/home/ozen/adhan-system/wifi_watchdog.sh
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

**4. Enable and start it:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable wifi-watchdog
sudo systemctl start wifi-watchdog
```

**5. View live logs:**
```bash
tail -f /home/ozen/adhan-system/wifi_watchdog.log
```

---

## Configuration

All configurable values are at the top of `adhan_system.py`:

| Variable | Default | Description |
|---|---|---|
| `LATITUDE` | `29.6197` | Sugar Land, TX latitude |
| `LONGITUDE` | `-95.6350` | Sugar Land, TX longitude |
| `TIMEZONE` | `America/Chicago` | Local timezone |
| `ALADHAN_METHOD` | `2` | Prayer calculation method (2 = ISNA) |
| `ALADHAN_SCHOOL` | `1` | Asr calculation (1 = Hanafi) |
| `STARTUP_CATCHUP_WINDOW_MINUTES` | `10` | Catch-up window on restart |
| `MISFIRE_GRACE_SECONDS` | `300` | Grace period for late-firing jobs |
| `ADHAN_HARD_KILL_SECONDS` | `900` | Hard kill after 15 minutes |
| `FETCH_MAX_RETRIES` | `5` | API fetch retry attempts |

---

## Logs

Both scripts log to files in the adhan-system folder:

```bash
# Adhan system log
tail -f /home/ozen/adhan-system/adhan.log

# WiFi watchdog log
tail -f /home/ozen/adhan-system/wifi_watchdog.log
```
