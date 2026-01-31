"""Job scheduler - APScheduler for daily digest cron jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import config


class JobScheduler:
    """Manages scheduled jobs using APScheduler."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def add_digest_job(self, job_func):
        """Add the daily digest job.

        Args:
            job_func: Async function to run for digest generation.
        """
        # Parse cron schedule from config
        schedule = config.digest_schedule
        parts = schedule.split()

        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
        else:
            # Default to midnight UTC
            minute, hour, day, month, day_of_week = "0", "0", "*", "*", "*"

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id="daily_digest",
            replace_existing=True,
        )

        print(f"📅 Digest scheduled: {schedule}")

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        print("⏰ Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("⏰ Scheduler stopped")
