"""This module runs app.py at a regular interval to
automatically register the next event in the queue."""

# Imports
import os
import sentry_sdk
from apscheduler.schedulers.blocking import BlockingScheduler # Scheduler
from headless_chrome import rsvp # Cron function

# Pylint config
# pylint: disable=abstract-class-instantiated

# Initialize Sentry error tracking, if SENTRY_DSN set
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        SENTRY_DSN,
        traces_sample_rate=1.0
    )

# Get cron interval, set default if not set
MIN_INTERVAL = os.getenv('MIN_INTERVAL', '3')

# Create an instance of scheduler and add function.
scheduler = BlockingScheduler()
scheduler.add_job(rsvp, "interval", minutes=int(MIN_INTERVAL))

# Start scheduler
scheduler.start()

# Pylint config
# pylint: enable=abstract-class-instantiated
