from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.routes import auth, health, inspections, reports, template

app = FastAPI(
    title="Fieldreport API",
    description="API documentation for Fieldreport",
    version="1.0.0",
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
app.include_router(reports.router)
app.include_router(template.router)
