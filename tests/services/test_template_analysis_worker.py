from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.workers import template_analysis_worker


async def test_run_template_analysis_worker_does_not_sleep_when_job_is_available() -> None:
    with (
        patch.object(
            template_analysis_worker.template_analysis_pipeline,
            "process_next_template_analysis_job",
            AsyncMock(side_effect=[SimpleNamespace(id="job-1"), KeyboardInterrupt()]),
        ) as process_job,
        patch.object(template_analysis_worker.asyncio, "sleep", AsyncMock()) as sleep,
    ):
        try:
            await template_analysis_worker.run_template_analysis_worker()
        except KeyboardInterrupt:
            pass

    process_job.assert_awaited()
    sleep.assert_not_awaited()


async def test_run_template_analysis_worker_sleeps_when_no_job_is_available() -> None:
    with (
        patch.object(
            template_analysis_worker.template_analysis_pipeline,
            "process_next_template_analysis_job",
            AsyncMock(side_effect=[None, KeyboardInterrupt()]),
        ),
        patch.object(template_analysis_worker.asyncio, "sleep", AsyncMock()) as sleep,
    ):
        try:
            await template_analysis_worker.run_template_analysis_worker()
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("Expected KeyboardInterrupt")

    sleep.assert_awaited_once_with(
        template_analysis_worker.settings.template_analysis_worker_poll_seconds
    )


def test_main_starts_worker() -> None:
    def close_coroutine(coroutine):
        coroutine.close()

    with patch.object(template_analysis_worker.asyncio, "run", side_effect=close_coroutine) as run:
        template_analysis_worker.main()

    run.assert_called_once()


def test_module_main_branch_executes_worker_entrypoint() -> None:
    import runpy

    def close_coroutine(coroutine):
        coroutine.close()

    with patch("asyncio.run", side_effect=close_coroutine) as run:
        runpy.run_path(template_analysis_worker.__file__, run_name="__main__")

    run.assert_called_once()
