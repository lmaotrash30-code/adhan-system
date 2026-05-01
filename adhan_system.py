import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import subprocess
import threading
import random
import time
import os
import glob
import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

AUDIO_BASE_DIR     = "/home/ozen/adhan-system"
FAJR_AUDIO_DIR     = os.path.join(AUDIO_BASE_DIR, "fajr")
STANDARD_AUDIO_DIR = os.path.join(AUDIO_BASE_DIR, "standard")
FALLBACK_AUDIO     = os.path.join(AUDIO_BASE_DIR, "adhan.mp3")

# Sugar Land, TX
LATITUDE  = 29.6197
LONGITUDE = -95.6350
TIMEZONE  = "America/Chicago"
TZ        = ZoneInfo(TIMEZONE)   # single source of truth for all datetime calls

# Aladhan API  |  method=2 → ISNA  |  school=1 → Hanafi Asr
ALADHAN_METHOD = 2
ALADHAN_SCHOOL = 0

SKIP_PRAYERS = {"sunrise", "imsak", "midnight", "sunset", "firstthird", "lastthird"}

FETCH_MAX_RETRIES = 5
FETCH_RETRY_DELAY = 60  # seconds between retries

# If the script starts and a prayer was missed within this window, play it now.
STARTUP_CATCHUP_WINDOW_MINUTES = 10

# How long after the scheduled time a misfired job is still allowed to run.
MISFIRE_GRACE_SECONDS = 300  # 5 minutes

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

LOG_FILE = os.path.join(AUDIO_BASE_DIR, "adhan.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("adhan")

# ─────────────────────────────────────────────
# API URL
# ─────────────────────────────────────────────

def build_api_url() -> str:
    date_str = datetime.now(TZ).strftime("%d-%m-%Y")
    return (
        f"https://api.aladhan.com/v1/timings/{date_str}"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&method={ALADHAN_METHOD}&school={ALADHAN_SCHOOL}"
    )

# ─────────────────────────────────────────────
# AUDIO
# ─────────────────────────────────────────────

def pick_audio(prayer_name: str) -> str | None:
    is_fajr   = prayer_name.lower() == "fajr"
    audio_dir = FAJR_AUDIO_DIR if is_fajr else STANDARD_AUDIO_DIR
    label     = "Fajr" if is_fajr else "standard"

    candidates = []
    for ext in ("*.mp3", "*.wav", "*.ogg"):
        candidates.extend(glob.glob(os.path.join(audio_dir, ext)))

    if candidates:
        chosen = random.choice(candidates)
        log.info("Audio pool (%s): %d file(s) — picked: %s",
                 label, len(candidates), os.path.basename(chosen))
        return chosen

    log.warning("No files in %s — falling back to %s", audio_dir, FALLBACK_AUDIO)
    if os.path.isfile(FALLBACK_AUDIO):
        return FALLBACK_AUDIO

    log.error("Fallback audio missing: %s", FALLBACK_AUDIO)
    return None


ADHAN_HARD_KILL_SECONDS = 15 * 60  # 15 minutes — hard ceiling on any adhan playback

def _audio_worker(prayer_name: str, audio_file: str) -> None:
    """Runs in a background thread — plays audio without blocking the scheduler."""
    proc = None
    try:
        proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file],
        )
        try:
            proc.wait(timeout=ADHAN_HARD_KILL_SECONDS)
            if proc.returncode != 0:
                log.warning("ffplay exited with code %d for %s.", proc.returncode, prayer_name)
            else:
                log.info("Adhan finished for %s.", prayer_name.capitalize())
        except subprocess.TimeoutExpired:
            log.warning(
                "Adhan for %s exceeded %d minutes — force killing process.",
                prayer_name.capitalize(), ADHAN_HARD_KILL_SECONDS // 60,
            )
            proc.kill()
            proc.wait()  # reap the zombie process
            log.info("ffplay process killed for %s.", prayer_name.capitalize())
    except FileNotFoundError:
        log.error("ffplay not found — install with: sudo apt install ffmpeg")
    except Exception as e:
        log.exception("Unexpected error playing adhan for %s: %s", prayer_name, e)
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait()


def play_adhan(prayer_name: str) -> None:
    """Schedule adhan playback in a background thread so the scheduler stays free."""
    audio_file = pick_audio(prayer_name)
    if not audio_file:
        log.error("No audio available for %s — skipping.", prayer_name)
        return

    log.info("Playing adhan for %s", prayer_name.capitalize())
    thread = threading.Thread(
        target=_audio_worker,
        args=(prayer_name, audio_file),
        daemon=True,   # won't prevent the process from exiting on Ctrl+C
        name=f"adhan-{prayer_name.lower()}",
    )
    thread.start()

# ─────────────────────────────────────────────
# FETCH PRAYER TIMES
# ─────────────────────────────────────────────

timings: dict = {}


def fetch_prayer_times(retry: int = 0) -> bool:
    global timings
    url = build_api_url()
    log.info("Fetching prayer times (attempt %d)...", retry + 1)
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            raise ValueError(f"Unexpected API code: {data.get('code')}")

        timings = data["data"]["timings"]
        meta    = data["data"].get("meta", {})
        log.info(
            "Prayer times updated | method: %s | timezone: %s",
            meta.get("method", {}).get("name", "?"),
            meta.get("timezone", "?"),
        )
        return True

    except requests.exceptions.ConnectionError:
        log.warning("Network unavailable.")
    except requests.exceptions.Timeout:
        log.warning("Request timed out.")
    except requests.exceptions.HTTPError as e:
        log.error("HTTP error: %s", e)
    except (KeyError, ValueError) as e:
        log.error("Unexpected API response format: %s", e)
    except Exception as e:
        log.exception("Unexpected error: %s", e)

    if retry < FETCH_MAX_RETRIES:
        log.info("Retrying in %d seconds...", FETCH_RETRY_DELAY)
        time.sleep(FETCH_RETRY_DELAY)
        return fetch_prayer_times(retry + 1)

    log.error("All %d fetch attempts failed. Will retry at midnight.", FETCH_MAX_RETRIES)
    return False

# ─────────────────────────────────────────────
# STARTUP CATCH-UP
# ─────────────────────────────────────────────

def catchup_missed_prayers() -> None:
    """
    On startup, check if any prayer was scheduled within the last
    STARTUP_CATCHUP_WINDOW_MINUTES minutes. If so, play it immediately.
    This handles the case where the script is restarted just after a prayer time.
    """
    now    = datetime.now(TZ)
    window = timedelta(minutes=STARTUP_CATCHUP_WINDOW_MINUTES)

    for prayer, time_str in timings.items():
        if prayer.lower() in SKIP_PRAYERS:
            continue
        try:
            clean = time_str.split(" ")[0]
            hour, minute = map(int, clean.split(":"))
        except ValueError:
            continue

        prayer_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        diff = now - prayer_dt  # positive means it's in the past

        if timedelta(0) < diff <= window:
            log.warning(
                "Startup catch-up: %s was missed by %dm %ds — playing now.",
                prayer.capitalize(),
                int(diff.total_seconds() // 60),
                int(diff.total_seconds() % 60),
            )
            play_adhan(prayer)

# ─────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────

def job_listener(event):
    if event.exception:
        log.error("Job '%s' raised an exception: %s", event.job_id, event.exception)
    else:
        log.debug("Job '%s' completed.", event.job_id)


def schedule_prayers(scheduler: BlockingScheduler) -> None:
    for job in scheduler.get_jobs():
        if job.id.startswith("prayer_"):
            job.remove()

    if not timings:
        log.error("No timings available — cannot schedule prayers.")
        return

    log.info("--- Prayer Schedule | Sugar Land, TX | %s ---",
             datetime.now(TZ).strftime("%Y-%m-%d"))

    for prayer, time_str in timings.items():
        if prayer.lower() in SKIP_PRAYERS:
            continue
        try:
            clean = time_str.split(" ")[0]
            hour, minute = map(int, clean.split(":"))
        except ValueError:
            log.warning("Cannot parse '%s' for %s — skipping.", time_str, prayer)
            continue

        pool = "[Fajr pool]" if prayer.lower() == "fajr" else "[standard pool]"
        log.info("  %-10s %02d:%02d  %s", prayer.capitalize(), hour, minute, pool)

        scheduler.add_job(
            play_adhan,
            "cron",
            id=f"prayer_{prayer.lower()}",
            hour=hour,
            minute=minute,
            args=[prayer],
            replace_existing=True,
            misfire_grace_time=MISFIRE_GRACE_SECONDS,
        )

    log.info("-" * 50)


def daily_refresh() -> None:
    log.info("Daily refresh triggered.")
    if fetch_prayer_times():
        schedule_prayers(scheduler)

# ─────────────────────────────────────────────
# STARTUP CHECKS
# ─────────────────────────────────────────────

def check_audio_dirs() -> None:
    for label, path in [("Fajr", FAJR_AUDIO_DIR), ("Standard", STANDARD_AUDIO_DIR)]:
        if not os.path.isdir(path):
            log.warning("%s audio dir not found: %s (will fall back to %s)",
                        label, path, FALLBACK_AUDIO)
        else:
            files = []
            for ext in ("*.mp3", "*.wav", "*.ogg"):
                files.extend(glob.glob(os.path.join(path, ext)))
            log.info("%s audio pool: %d file(s) in %s", label, len(files), path)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

scheduler = BlockingScheduler(timezone=TIMEZONE)
scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

check_audio_dirs()

if not fetch_prayer_times():
    log.critical("Could not fetch prayer times on startup. Check network and restart.")
    sys.exit(1)

# Play any prayer missed within the last 10 minutes before scheduling
catchup_missed_prayers()

schedule_prayers(scheduler)

scheduler.add_job(
    daily_refresh,
    "cron",
    id="daily_fetch",
    hour=0,
    minute=5,
    replace_existing=True,
)

log.info("System running | Sugar Land, TX | Press Ctrl+C to stop.")

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    log.info("System stopped by user.")
except Exception as e:
    log.exception("Scheduler crashed: %s", e)
    sys.exit(1)