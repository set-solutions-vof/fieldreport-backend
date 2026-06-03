import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.db import connection
from src.llm import client_factory
from src.routes import auth, health, inspections, onboarding, reports, template, uploads
from src.storage import blob
from src.workers import audio_pipeline_worker, template_analysis_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connection.create_pool()
    await blob.ensure_containers()

    client_factory.get_gpt4o_client()
    client_factory.get_deepseek_client()
    client_factory.get_gpt4o_transcribe_client()

    audio_task = asyncio.create_task(audio_pipeline_worker.run_audio_pipeline_worker())

    template_task = asyncio.create_task(template_analysis_worker.run_template_analysis_worker())

    yield

    audio_task.cancel()

    template_task.cancel()
    await asyncio.gather(audio_task, template_task, return_exceptions=True)
    await connection.close_pool()


app = FastAPI(
    title="Fieldreport API",
    description="API documentation for Fieldreport",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inspections.router)
app.include_router(onboarding.router)
app.include_router(reports.router)
app.include_router(template.router)
app.include_router(uploads.router)
