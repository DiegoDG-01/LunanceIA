import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from infrastructure.scheduler.jobs import (
    process_subscriptions_job,
    process_investment_yield_job,
    process_recurring_income_job,
)

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=utc)

    def start(self):
        self.scheduler.add_job(
            process_subscriptions_job,
            trigger=CronTrigger(hour=0),
            id="process_subscriptions_job",
            name="Process daily subscriptions",
            replace_existing=True,
        )

        self.scheduler.add_job(
            process_investment_yield_job,
            trigger=CronTrigger(hour=12, minute=0),
            id="process_investment_yield_job",
            name="Process investment yield job",
            replace_existing=True,
        )

        self.scheduler.add_job(
            process_recurring_income_job,
            trigger=CronTrigger(hour=0, minute=15),
            id="process_recurring_incomes_job",
            name="Process recurring incomes",
            replace_existing=True,
        )

        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")


scheduler_service = SchedulerService()
