import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app, lifespan


async def test_lifespan_initialises_all_services() -> None:
    worker_started = asyncio.Event()

    async def fake_worker():
        worker_started.set()
        await asyncio.sleep(999)

    with (
        patch("src.main.connection.create_pool", AsyncMock()) as create_pool,
        patch("src.main.blob.ensure_containers", AsyncMock()) as ensure_containers,
        patch("src.main.client_factory.get_gpt4o_client", MagicMock()) as get_gpt4o,
        patch("src.main.client_factory.get_deepseek_client", MagicMock()) as get_deepseek,
        patch("src.main.client_factory.get_gpt4o_transcribe_client", MagicMock()) as get_transcribe,
        patch(
            "src.main.audio_pipeline_worker.run_audio_pipeline_worker",
            return_value=fake_worker(),
        ),
        patch(
            "src.main.template_analysis_worker.run_template_analysis_worker",
            return_value=fake_worker(),
        ),
        patch("src.main.connection.close_pool", AsyncMock()) as close_pool,
    ):
        async with lifespan(app):
            pass

    create_pool.assert_awaited_once()
    ensure_containers.assert_awaited_once()
    get_gpt4o.assert_called_once()
    get_deepseek.assert_called_once()
    get_transcribe.assert_called_once()
    close_pool.assert_awaited_once()
