from unittest.mock import AsyncMock, patch

from src.workers import audio_pipeline_worker


async def test_run_audio_pipeline_worker_processes_claimed_report() -> None:
    report = {"id": "report-id"}

    with (
        patch.object(
            audio_pipeline_worker.report_queries,
            "claim_next_audio_pipeline_report",
            AsyncMock(return_value=report),
        ) as claim_report,
        patch.object(
            audio_pipeline_worker.audio_pipeline,
            "run_audio_pipeline",
            AsyncMock(side_effect=KeyboardInterrupt),
        ) as run_pipeline,
    ):
        try:
            await audio_pipeline_worker.run_audio_pipeline_worker()
        except KeyboardInterrupt:
            pass

    claim_report.assert_awaited_once()
    run_pipeline.assert_awaited_once_with("report-id")


async def test_run_audio_pipeline_worker_continues_after_report_failure() -> None:
    report = {"id": "report-id"}

    with (
        patch.object(
            audio_pipeline_worker.report_queries,
            "claim_next_audio_pipeline_report",
            AsyncMock(side_effect=[report, KeyboardInterrupt()]),
        ),
        patch.object(
            audio_pipeline_worker.audio_pipeline,
            "run_audio_pipeline",
            AsyncMock(side_effect=ValueError("failed")),
        ) as run_pipeline,
    ):
        try:
            await audio_pipeline_worker.run_audio_pipeline_worker()
        except KeyboardInterrupt:
            raised = True
        else:
            raised = False

    assert raised is True
    run_pipeline.assert_awaited_once_with("report-id")


async def test_run_audio_pipeline_worker_sleeps_when_no_report_is_available() -> None:
    with (
        patch.object(
            audio_pipeline_worker.report_queries,
            "claim_next_audio_pipeline_report",
            AsyncMock(side_effect=[None, KeyboardInterrupt()]),
        ),
        patch.object(audio_pipeline_worker.asyncio, "sleep", AsyncMock()) as sleep,
    ):
        try:
            await audio_pipeline_worker.run_audio_pipeline_worker()
        except KeyboardInterrupt:
            raised = True
        else:
            raised = False

    assert raised is True
    sleep.assert_awaited_once_with(
        audio_pipeline_worker.settings.audio_pipeline_worker_poll_seconds
    )


def test_audio_pipeline_worker_main_starts_worker() -> None:
    def close_coroutine(coroutine):
        coroutine.close()

    with patch.object(audio_pipeline_worker.asyncio, "run", side_effect=close_coroutine) as run:
        audio_pipeline_worker.main()

    run.assert_called_once()


def test_audio_pipeline_worker_module_main_branch_executes_entrypoint() -> None:
    import runpy

    def close_coroutine(coroutine):
        coroutine.close()

    with patch("asyncio.run", side_effect=close_coroutine) as run:
        runpy.run_path(audio_pipeline_worker.__file__, run_name="__main__")

    run.assert_called_once()
