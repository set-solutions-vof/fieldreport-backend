from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.workers import template_analysis_worker


async def test_run_template_analysis_worker_returns_after_one_iteration() -> None:
    with patch.object(
        template_analysis_worker.template_analysis,
        "process_next_template_analysis_job",
        AsyncMock(return_value=SimpleNamespace(id="job-1")),
    ) as process_job:
        await template_analysis_worker.run_template_analysis_worker(True)

    process_job.assert_awaited_once()


async def test_run_template_analysis_worker_sleeps_when_no_job_is_available() -> None:
    with (
        patch.object(
            template_analysis_worker.template_analysis,
            "process_next_template_analysis_job",
            AsyncMock(side_effect=[None, KeyboardInterrupt()]),
        ),
        patch.object(template_analysis_worker.asyncio, "sleep", AsyncMock()) as sleep,
    ):
        try:
            await template_analysis_worker.run_template_analysis_worker(False)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("Expected KeyboardInterrupt")

    sleep.assert_awaited_once_with(
        template_analysis_worker.settings.template_analysis_worker_poll_seconds
    )


def test_main_runs_worker_with_cli_arguments() -> None:
    with (
        patch.object(template_analysis_worker.argparse.ArgumentParser, "parse_args") as parse_args,
        patch.object(template_analysis_worker.asyncio, "run") as run,
    ):
        parse_args.return_value = SimpleNamespace(once=True)
        template_analysis_worker.main()

    run.assert_called_once()


def test_module_main_branch_executes_worker_entrypoint() -> None:
    import runpy

    with (
        patch.object(template_analysis_worker.argparse.ArgumentParser, "parse_args") as parse_args,
        patch("asyncio.run") as run,
    ):
        parse_args.return_value = SimpleNamespace(once=True)
        runpy.run_module("src.workers.template_analysis_worker", run_name="__main__")

    run.assert_called_once()
