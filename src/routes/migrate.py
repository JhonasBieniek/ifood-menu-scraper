"""
Rotas da API de migração.

Endpoints:
  POST /api/migrate              → inicia job, retorna jobId
  GET  /api/migrate/{job_id}     → polling: status + resultado
  GET  /api/migrate/{job_id}/events → SSE: progresso em tempo real
  GET  /api/health               → health check
"""

import json
import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from src.config import config
from src.jobs.store import (
    create_job, get_job, update_job, add_progress,
    get_stats, JobStatus,
)
from src.scraper.migration import run_migration

router = APIRouter()

# Contador de jobs ativos (sem Redis, em memória)
_active_jobs: int = 0


# ─── Autenticação opcional por API Key ───────────────────────

def check_api_key(request: Request):
    if not config.API_KEY:
        return  # auth desabilitada
    key = request.headers.get("x-api-key")
    if key != config.API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente.")


# ─── Schema de entrada ────────────────────────────────────────

class MigrateRequest(BaseModel):
    url: str  # não usamos HttpUrl para manter mensagem de erro customizada


# ─── POST /api/migrate ────────────────────────────────────────

@router.post("/migrate", status_code=202, dependencies=[Depends(check_api_key)])
async def start_migration(body: MigrateRequest):
    global _active_jobs

    if _active_jobs >= config.MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {config.MAX_CONCURRENT_JOBS} jobs simultâneos atingido. Tente novamente.",
        )

    job = create_job(body.url)
    _active_jobs += 1
    update_job(job.id, status=JobStatus.RUNNING)

    # Callback assíncrono de progresso: grava no job store
    async def on_progress(message: str, step: int | None = None):
        add_progress(job.id, message, step)

    # Inicia o scraping em background (não bloqueia a resposta HTTP)
    async def run():
        global _active_jobs
        try:
            result = await run_migration(body.url, on_progress)
            update_job(job.id, status=JobStatus.DONE, result=result)
        except Exception as e:
            err = str(e).strip() or f"{type(e).__name__}: {e!r}"
            update_job(job.id, status=JobStatus.ERROR, error=err)
        finally:
            _active_jobs -= 1

    asyncio.create_task(run())

    return {
        "job_id": job.id,
        "status": JobStatus.PENDING,
        "status_url": f"/api/migrate/{job.id}",
        "events_url": f"/api/migrate/{job.id}/events",
    }


# ─── GET /api/migrate/{job_id} ────────────────────────────────

@router.get("/migrate/{job_id}", dependencies=[Depends(check_api_key)])
async def get_migration_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    return {
        "id": job.id,
        "url": job.url,
        "status": job.status,
        "progress": [
            {"message": p.message, "step": p.step, "timestamp": p.timestamp}
            for p in job.progress
        ],
        "result": job.result if job.status == JobStatus.DONE else None,
        "error": job.error if job.status == JobStatus.ERROR else None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


# ─── GET /api/migrate/{job_id}/events (SSE) ──────────────────

@router.get("/migrate/{job_id}/events")
async def stream_events(job_id: str, request: Request):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    async def event_generator():
        last_index = 0

        # Envia eventos de progresso já existentes (se job já estava rodando)
        while True:
            if await request.is_disconnected():
                break

            current = get_job(job_id)
            if not current:
                break

            # Envia novos eventos de progresso
            while last_index < len(current.progress):
                event = current.progress[last_index]
                payload = json.dumps({"message": event.message, "step": event.step})
                yield f"event: progress\ndata: {payload}\n\n"
                last_index += 1

            # Job finalizado
            if current.status == JobStatus.DONE:
                yield f"event: done\ndata: {json.dumps({'result': current.result})}\n\n"
                break

            if current.status == JobStatus.ERROR:
                yield f"event: error\ndata: {json.dumps({'message': current.error})}\n\n"
                break

            # Keep-alive para evitar timeout do proxy
            yield ": keepalive\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Desativa buffering do Nginx
        },
    )


# ─── GET /api/health ─────────────────────────────────────────

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "active_jobs": _active_jobs,
        "max_concurrent_jobs": config.MAX_CONCURRENT_JOBS,
        "strategy": config.SCRAPER_STRATEGY,
        "max_items_detail": config.MAX_ITEMS_DETAIL,
        "job_stats": get_stats(),
    }
