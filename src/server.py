from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.jobs.store import start_cleanup_task
from src.routes.migrate import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_cleanup_task()
    print(f"\nifood-migrator-py rodando em http://{config.HOST}:{config.PORT}")
    print(f"   Estratégia: {config.SCRAPER_STRATEGY}\n")
    yield
    # Shutdown (cleanup se necessário)


app = FastAPI(
    title="ifood-migrator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Api-Key"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "ifood-migrator-py",
        "strategy": config.SCRAPER_STRATEGY,
        "endpoints": {
            "start": "POST /api/migrate",
            "status": "GET /api/migrate/{job_id}",
            "events": "GET /api/migrate/{job_id}/events",
            "health": "GET /api/health",
        },
    }
