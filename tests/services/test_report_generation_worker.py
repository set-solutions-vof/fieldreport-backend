from unittest.mock import AsyncMock, patch

from src.workers import report_generation_worker


async def test_run_report_generation_worker_processes_claimed_report() -> None:
    report = {"id": "report-id"}

    with (
        patch.object(
            report_generation_worker.queries,
            "claim_next_report_for_generation",
            AsyncMock(return_value=report),
        ) as claim_report,
        patch.object(
            report_generation_worker.pipeline,
            "run_report_generation",
            AsyncMock(side_effect=KeyboardInterrupt),
        ) as run_pipeline,
    ):
        try:
            await report_generation_worker.run_report_generation_worker()
        except KeyboardInterrupt:
            pass

    claim_report.assert_awaited_once()
    run_pipeline.assert_awaited_once_with("report-id")


async def test_run_report_generation_worker_continues_after_report_failure() -> None:
    report = {"id": "report-id"}

    with (
        patch.object(
            report_generation_worker.queries,
            "claim_next_report_for_generation",
            AsyncMock(side_effect=[report, KeyboardInterrupt()]),
        ),
        patch.object(
            report_generation_worker.pipeline,
            "run_report_generation",
            AsyncMock(side_effect=ValueError("failed")),
        ) as run_pipeline,
    ):
        try:
            await report_generation_worker.run_report_generation_worker()
        except KeyboardInterrupt:
            raised = True
        else:
            raised = False

    assert raised is True
    run_pipeline.assert_awaited_once_with("report-id")


async def test_run_report_generation_worker_sleeps_when_no_report_is_available() -> None:
    with (
        patch.object(
            report_generation_worker.queries,
            "claim_next_report_for_generation",
            AsyncMock(side_effect=[None, KeyboardInterrupt()]),
        ),
        patch.object(report_generation_worker.asyncio, "sleep", AsyncMock()) as sleep,
    ):
        try:
            await report_generation_worker.run_report_generation_worker()
        except KeyboardInterrupt:
            raised = True
        else:
            raised = False

    assert raised is True
    sleep.assert_awaited_once_with(
        report_generation_worker.settings.report_generation_worker_poll_seconds
    )
