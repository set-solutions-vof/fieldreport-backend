import asyncio

from loguru import logger

from src.config import settings
from src.db import report_queries
from src.services import audio_pipeline


async def run_audio_pipeline_worker() -> None:
    logger.info("Audio pipeline worker started")
    while True:
        report = await report_queries.claim_next_audio_pipeline_report()

        if report is None:
            await asyncio.sleep(settings.audio_pipeline_worker_poll_seconds)
            continue

        try:
            await audio_pipeline.run_audio_pipeline(str(report["id"]))
        except Exception as error:
            logger.exception("Audio pipeline report {} failed: {}", report["id"], error)


def main() -> None:
    asyncio.run(run_audio_pipeline_worker())


if __name__ == "__main__":
    main()
