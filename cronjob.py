import os
import sentry_sdk

SENTRY_DSN = os.getenv(['SENTRY_DSN'])
if SENTRY_DSN:
    sentry_sdk.init(
        SENTRY_DSN,
        traces_sample_rate=1.0
    )

# Package Scheduler.
from apscheduler.schedulers.blocking import BlockingScheduler

# Main cronjob function.
from headless_chrome import rsvp

MIN_INTERVAL = os.getenv('MIN_INTERVAL',3)

# Create an instance of scheduler and add function.
scheduler = BlockingScheduler()
scheduler.add_job(rsvp, "interval", minutes=int(MIN_INTERVAL))

scheduler.start()
