from fastapi import FastAPI

from src.routes import auth, health, reports

app = FastAPI(title="Fieldreport API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(reports.router)
