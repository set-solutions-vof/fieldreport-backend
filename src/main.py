from fastapi import FastAPI

from src.routes import health

app = FastAPI(title="Fieldreport API")

app.include_router(health.router)
