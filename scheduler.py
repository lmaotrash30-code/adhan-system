from apscheduler.schedulers.blocking import BlockingScheduler
import datetime

def job():
    print("Adhan trigger:", datetime.datetime.now())

scheduler = BlockingScheduler()

# Example: run job every day at 00:00:05
scheduler.add_job(job, 'cron', hour=15, minute=42, second=0)

scheduler.start()