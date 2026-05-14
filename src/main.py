from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware

from src.routes import auth, health, reports, template

app = FastAPI(title="Fieldreport API")
frontend_dist_path = Path(__file__).resolve().parents[1] / "tmp-fieldreport-frontend" / "dist"
frontend_index_path = frontend_dist_path / "index.html"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(template.router)


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    if not frontend_index_path.exists():
        raise HTTPException(status_code=404, detail="Not Found")

    requested_path = (frontend_dist_path / path).resolve()

    if path and frontend_dist_path.resolve() in requested_path.parents and requested_path.is_file():
        return FileResponse(requested_path)

    return FileResponse(frontend_index_path)
