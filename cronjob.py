# Imports
import os
import sentry_sdk

# Initialize Sentry error tracking, if SENTRY_DSN set
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        SENTRY_DSN,
        traces_sample_rate=1.0
    )

# More imports
from apscheduler.schedulers.blocking import BlockingScheduler # Scheduler
from headless_chrome import rsvp # Cron function

# Get cron interval, set default if not set
MIN_INTERVAL = os.getenv('MIN_INTERVAL',3)

# Create an instance of scheduler and add function.
scheduler = BlockingScheduler()
scheduler.add_job(rsvp, "interval", minutes=int(MIN_INTERVAL))

# Start scheduler
scheduler.start()
