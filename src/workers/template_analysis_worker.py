import argparse
import asyncio

from loguru import logger

from src.config import settings
from src.services import template_analysis


async def run_template_analysis_worker(run_once: bool) -> None:
    logger.info("Template analysis worker started (run_once={})", run_once)
    while True:
        job = await template_analysis.process_next_template_analysis_job()

        if run_once:
            return

        if job is None:
            await asyncio.sleep(settings.template_analysis_worker_poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    arguments = parser.parse_args()

    asyncio.run(run_template_analysis_worker(arguments.once))


if __name__ == "__main__":
    main()
