from __future__ import annotations

"""
Rotas da API de migração.

Endpoints:
  POST /api/migrate                    → inicia job, retorna jobId
  POST /api/migrate/{job_id}/cancel    → cancela job em andamento
  GET  /api/migrate/{job_id}           → polling: status + resultado
  GET  /api/migrate/{job_id}/events    → SSE: progresso em tempo real
  GET  /api/health                     → health check
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.auth import check_api_key
from src.config import config
from src.db.database import get_db
from src.jobs.models import JobStatus
from src.jobs.store import (
    add_progress,
    cancel_job,
    clear_cancel,
    create_job,
    get_job,
    get_stats,
    is_cancelled,
    register_running_task,
    request_cancel,
    unregister_running_task,
    update_job,
)
from src.scraper.resolver import extract_merchant_id_or_raise

router = APIRouter()

_active_jobs: int = 0
_TERMINAL = frozenset({JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED})


class MigrateRequest(BaseModel):
    url: str


@router.post("/migrate", status_code=202, dependencies=[Depends(check_api_key)])
async def start_migration(body: MigrateRequest):
    global _active_jobs

    try:
        extract_merchant_id_or_raise(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if _active_jobs >= config.MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {config.MAX_CONCURRENT_JOBS} jobs simultâneos atingido. Tente novamente.",
        )

    job = await create_job(body.url)
    _active_jobs += 1
    await update_job(job.id, status=JobStatus.RUNNING)

    async def on_progress(message: str, step: int | None = None):
        if is_cancelled(job.id):
            raise asyncio.CancelledError()
        await add_progress(job.id, message, step)

    async def run():
        global _active_jobs
        from src.scraper.migration import run_migration

        try:
            result = await run_migration(body.url, on_progress)
            if is_cancelled(job.id):
                await update_job(
                    job.id,
                    status=JobStatus.CANCELLED,
                    error="Cancelado pelo usuário",
                )
            else:
                await update_job(job.id, status=JobStatus.DONE, result=result)
        except asyncio.CancelledError:
            if not is_cancelled(job.id):
                request_cancel(job.id)
            await update_job(
                job.id,
                status=JobStatus.CANCELLED,
                error="Cancelado pelo usuário",
            )
        except Exception as e:
            if is_cancelled(job.id):
                await update_job(
                    job.id,
                    status=JobStatus.CANCELLED,
                    error="Cancelado pelo usuário",
                )
            else:
                err = str(e).strip() or f"{type(e).__name__}: {e!r}"
                await update_job(job.id, status=JobStatus.ERROR, error=err)
        finally:
            unregister_running_task(job.id)
            clear_cancel(job.id)
            _active_jobs -= 1

    task = asyncio.create_task(run())
    register_running_task(job.id, task)

    return {
        "job_id": job.id,
        "status": JobStatus.PENDING.value,
        "status_url": f"/api/migrate/{job.id}",
        "events_url": f"/api/migrate/{job.id}/events",
        "cancel_url": f"/api/migrate/{job.id}/cancel",
    }


@router.post("/migrate/{job_id}/cancel", dependencies=[Depends(check_api_key)])
async def cancel_migration(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    if job.status in _TERMINAL:
        raise HTTPException(
            status_code=400,
            detail=f"Job já finalizado com status '{job.status.value}'.",
        )

    updated = await cancel_job(job_id)
    return {
        "id": job_id,
        "status": updated.status.value if updated else JobStatus.CANCELLED.value,
    }


@router.get("/migrate/{job_id}", dependencies=[Depends(check_api_key)])
async def get_migration_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    return _job_response(job)


def _job_response(job):
    return {
        "id": job.id,
        "url": job.url,
        "status": job.status.value,
        "progress": [
            {"message": p.message, "step": p.step, "timestamp": p.timestamp}
            for p in job.progress
        ],
        "result": job.result if job.status == JobStatus.DONE else None,
        "error": job.error
        if job.status in (JobStatus.ERROR, JobStatus.CANCELLED)
        else None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.get("/migrate/{job_id}/events")
async def stream_events(job_id: str, request: Request):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    async def event_generator():
        last_index = 0

        while True:
            if await request.is_disconnected():
                break

            current = await get_job(job_id)
            if not current:
                break

            while last_index < len(current.progress):
                event = current.progress[last_index]
                payload = json.dumps({"message": event.message, "step": event.step})
                yield f"event: progress\ndata: {payload}\n\n"
                last_index += 1

            if current.status == JobStatus.DONE:
                yield f"event: done\ndata: {json.dumps({'result': current.result})}\n\n"
                break

            if current.status == JobStatus.ERROR:
                yield f"event: error\ndata: {json.dumps({'message': current.error})}\n\n"
                break

            if current.status == JobStatus.CANCELLED:
                yield f"event: cancelled\ndata: {json.dumps({'message': current.error or 'Cancelado'})}\n\n"
                break

            yield ": keepalive\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def health():
    try:
        get_db()
        database_status = "ok"
    except RuntimeError:
        database_status = "unavailable"

    stats = await get_stats()
    return {
        "status": "ok",
        "database": database_status,
        "auth_required": bool(config.API_KEY),
        "active_jobs": _active_jobs,
        "max_concurrent_jobs": config.MAX_CONCURRENT_JOBS,
        "strategy": config.SCRAPER_STRATEGY,
        "max_items_detail": config.MAX_ITEMS_DETAIL,
        "job_stats": stats,
    }
