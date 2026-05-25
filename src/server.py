from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import config
from src.db.database import close_db, init_db
from src.routes.history import router as history_router
from src.routes.migrate import router as migrate_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"\nifood-migrator-py rodando em http://{config.HOST}:{config.PORT}")
    print(f"   Interface web: http://{config.HOST}:{config.PORT}/")
    print(f"   Estratégia: {config.SCRAPER_STRATEGY}\n")
    yield
    await close_db()


app = FastAPI(
    title="ifood-migrator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Api-Key"],
)

app.include_router(migrate_router, prefix="/api")
app.include_router(history_router, prefix="/api")

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def web_ui():
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return {
            "service": "ifood-migrator-py",
            "message": "Interface web não encontrada. Verifique static/index.html",
        }
    return FileResponse(index)
