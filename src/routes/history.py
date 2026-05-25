from __future__ import annotations

"""Rotas de histórico de scrapings persistidos em SQLite."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth import check_api_key
from src.db.repository import get_repository
from src.jobs.models import JobStatus
from src.jobs.store import delete_job, get_job

router = APIRouter()


@router.get("/scrapes", dependencies=[Depends(check_api_key)])
async def list_scrapes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
):
    status_filter: JobStatus | None = None
    if status is not None:
        try:
            status_filter = JobStatus(status.lower())
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: {', '.join(s.value for s in JobStatus)}",
            ) from e

    result = await get_repository().list_history(
        limit=limit, offset=offset, status=status_filter
    )
    return {
        "items": [
            {
                "id": item.id,
                "url": item.url,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "store_name": item.store_name,
            }
            for item in result.items
        ],
        "total": result.total,
        "limit": result.limit,
        "offset": result.offset,
    }


@router.get("/scrapes/{job_id}", dependencies=[Depends(check_api_key)])
async def get_scrape_detail(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scraping não encontrado.")

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


@router.delete("/scrapes/{job_id}", dependencies=[Depends(check_api_key)])
async def delete_scrape(job_id: str):
    deleted = await delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scraping não encontrado.")
    return {"deleted": True, "id": job_id}
