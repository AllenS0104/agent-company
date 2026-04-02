"""FastAPI Web 服务"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..workflow.pipeline import Pipeline
from .auth import router as auth_router
from .routes import router

_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    if _pipeline is None:
        raise RuntimeError("Pipeline not initialized")
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = Pipeline()
    await _pipeline.setup()
    yield
    await _pipeline.teardown()
    _pipeline = None


app = FastAPI(
    title="Agent Company",
    description="🏢 多AI协作讨论与执行框架 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router)

# Serve built frontend in production (Docker)
dist_dir = Path(__file__).parent.parent.parent / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(dist_dir / "index.html"))


def start_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
