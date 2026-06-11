import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.config import settings
from src.db import connection
from src.llm import client_factory
from src.routes import (
    auth,
    health,
    inspections,
    invites,
    onboarding,
    reports,
    team,
    template,
    uploads,
    users,
)
from src.storage import blob
from src.workers import report_generation_worker, template_analysis_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connection.init_database()
    await blob.ensure_containers()

    client_factory.get_gpt4o_client()
    client_factory.get_deepseek_client()
    client_factory.get_gpt4o_transcribe_client()

    report_generation_task = asyncio.create_task(
        report_generation_worker.run_report_generation_worker(),
        name="report-generation-worker",
    )

    template_task = asyncio.create_task(
        template_analysis_worker.run_template_analysis_worker(),
        name="template-analysis-worker",
    )

    yield

    report_generation_task.cancel()

    template_task.cancel()
    await asyncio.gather(report_generation_task, template_task, return_exceptions=True)
    await blob.close_service_client()
    await connection.close_database()


app = FastAPI(
    title="Fieldreport API",
    description="API documentation for Fieldreport",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inspections.router)
app.include_router(onboarding.router)
app.include_router(invites.router)
app.include_router(team.router)
app.include_router(reports.router)
app.include_router(template.router)
app.include_router(uploads.router)
app.include_router(users.router)
