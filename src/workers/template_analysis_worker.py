import asyncio

from loguru import logger

from src.config import settings
from src.pipelines import template_analysis_pipeline


async def run_template_analysis_worker() -> None:
    logger.info("Template analysis worker started")
    while True:
        job = await template_analysis_pipeline.process_next_template_analysis_job()

        if job is None:
            await asyncio.sleep(settings.template_analysis_worker_poll_seconds)


def main() -> None:
    asyncio.run(run_template_analysis_worker())


if __name__ == "__main__":
    main()
