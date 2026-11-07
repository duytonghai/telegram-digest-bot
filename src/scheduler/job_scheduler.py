"""Job scheduler - APScheduler for daily digest cron jobs."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import timezone

from ..config import config


class JobScheduler:
    """Manages scheduled jobs using APScheduler."""

    def __init__(self, event_loop=None):
        """Initialize scheduler with event loop.

        Args:
            event_loop: The asyncio event loop to use. If None, uses current loop.
        """
        self.event_loop = event_loop or asyncio.get_event_loop()
        # Pass the event loop to scheduler
        self.scheduler = AsyncIOScheduler(event_loop=self.event_loop)

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
            timezone=timezone.utc,  # Explicitly set UTC timezone
        )

        # Wrap async job to handle exceptions and logging
        async def job_wrapper():
            try:
                print(f"\n⏰ Scheduled job triggered at {asyncio.get_event_loop().time()}")
                await job_func()
            except Exception as e:
                print(f"❌ Scheduled job failed: {e}")
                import traceback
                traceback.print_exc()

        job = self.scheduler.add_job(
            job_wrapper,
            trigger=trigger,
            id="daily_digest",
            replace_existing=True,
            # Allow job to run even if missed by up to 6 hours (in seconds)
            misfire_grace_time=6*3600,
            # If multiple runs were missed, only run once
            coalesce=True,
            # Set max_instances to prevent overlapping runs
            max_instances=1,
        )

        print(f"📅 Digest scheduled: {schedule}")
        print(f"   Misfire grace time: 6 hours")

    def show_next_run(self):
        """Print the next scheduled run time."""
        scheduled_job = self.scheduler.get_job("daily_digest")
        if scheduled_job and scheduled_job.next_run_time:
            from datetime import datetime
            now = datetime.now(timezone.utc)
            next_run = scheduled_job.next_run_time
            time_until = next_run - now
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            print(f"⏰ Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   (in {hours}h {minutes}m from now)")

    def start(self):
        """Start the scheduler."""
        from datetime import datetime
        self.scheduler.start()
        print(f"⏰ Scheduler started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("⏰ Scheduler stopped")
