import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app, lifespan


async def test_lifespan_initialises_all_services() -> None:
    worker_started = asyncio.Event()

    async def fake_worker():
        worker_started.set()
        await asyncio.sleep(999)

    with (
        patch("src.main.connection.init_database", AsyncMock()) as init_database,
        patch("src.main.blob.ensure_containers", AsyncMock()) as ensure_containers,
        patch("src.main.client_factory.get_gpt4o_client", MagicMock()) as get_gpt4o,
        patch(
            "src.main.client_factory.get_whisper_transcribe_client",
            MagicMock(),
        ) as get_whisper,
        patch("src.main.blob.close_service_client", AsyncMock()) as close_blob,
        patch(
            "src.main.report_generation_worker.run_report_generation_worker",
            return_value=fake_worker(),
        ),
        patch("src.main.connection.close_database", AsyncMock()) as close_database,
    ):
        async with lifespan(app):
            pass

    init_database.assert_awaited_once()
    ensure_containers.assert_awaited_once()
    get_gpt4o.assert_called_once()
    get_whisper.assert_called_once()
    close_blob.assert_awaited_once()
    close_database.assert_awaited_once()
