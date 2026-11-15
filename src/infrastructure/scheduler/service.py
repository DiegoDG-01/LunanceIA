import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from infrastructure.scheduler.jobs import (
    process_investment_yield_job,
    process_position_maturity_job,
    process_recurring_income_job,
    process_subscriptions_job,
    purge_auth_data_job,
    purge_idempotency_keys_job,
)
from infrastructure.scheduler.market_data_jobs import (
    sync_instrument_catalog_job,
    sync_market_data_job,
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

        # Corre después del job de rendimientos: el día del vencimiento
        # todavía rinde y este job entrega el rendimiento completo.
        self.scheduler.add_job(
            process_position_maturity_job,
            trigger=CronTrigger(hour=12, minute=30),
            id="process_position_maturity_job",
            name="Process matured investment positions",
            replace_existing=True,
        )

        self.scheduler.add_job(
            process_recurring_income_job,
            trigger=CronTrigger(hour=0, minute=15),
            id="process_recurring_incomes_job",
            name="Process recurring incomes",
            replace_existing=True,
        )

        self.scheduler.add_job(
            purge_auth_data_job,
            trigger=CronTrigger(hour=3, minute=0),
            id="purge_auth_data_job",
            name="Purge expired sessions, auth events, pending signups and reset tokens",
            replace_existing=True,
        )

        self.scheduler.add_job(
            purge_idempotency_keys_job,
            trigger=CronTrigger(hour=3, minute=30),
            id="purge_idempotency_keys_job",
            name="Purge idempotency keys older than 24 h",
            replace_existing=True,
        )

        # Las bolsas cierran entre 20:00 y 21:00 UTC: a la 01:00 ya hay cierre del día. La
        # corrida de las 13:00 recoge lo que falló y las correcciones de los proveedores.
        self.scheduler.add_job(
            sync_market_data_job,
            trigger=CronTrigger(hour="1,13", minute=0),
            id="sync_market_data_job",
            name="Sync daily closes and FX rates",
            replace_existing=True,
        )

        self.scheduler.add_job(
            sync_instrument_catalog_job,
            trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="sync_instrument_catalog_job",
            name="Sync the BMV/BIVA and SIC instrument catalog",
            replace_existing=True,
        )

        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")


scheduler_service = SchedulerService()
