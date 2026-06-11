import asyncio

from loguru import logger

from src.config import settings
from src.db.report import queries
from src.pipelines.report_generation import pipeline


async def run_report_generation_worker() -> None:
    logger.info("Report generation worker started")
    while True:
        try:
            report = await queries.claim_next_report_for_generation()

            if report is None:
                await asyncio.sleep(settings.report_generation_worker_poll_seconds)
                continue

            await pipeline.run_report_generation(str(report["id"]))
        except Exception as error:
            logger.exception(error)
            await asyncio.sleep(5)
