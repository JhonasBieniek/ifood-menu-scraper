from __future__ import annotations

import asyncio
import uuid

from src.db.repository import get_repository
from src.jobs.models import Job, JobStatus, ProgressEvent

_active_cache: dict[str, Job] = {}
_cancelled_ids: set[str] = set()
_running_tasks: dict[str, asyncio.Task] = {}


def register_running_task(job_id: str, task: asyncio.Task) -> None:
    _running_tasks[job_id] = task


def unregister_running_task(job_id: str) -> None:
    _running_tasks.pop(job_id, None)


def request_cancel(job_id: str) -> None:
    _cancelled_ids.add(job_id)


def is_cancelled(job_id: str) -> bool:
    return job_id in _cancelled_ids


def clear_cancel(job_id: str) -> None:
    _cancelled_ids.discard(job_id)


async def create_job(url: str) -> Job:
    job = Job(id=str(uuid.uuid4()), url=url)
    repo = get_repository()
    await repo.create(job)
    _active_cache[job.id] = job
    return job


async def get_job(job_id: str) -> Job | None:
    if job_id in _active_cache:
        return _active_cache[job_id]
    return await get_repository().get(job_id)


async def update_job(job_id: str, **kwargs) -> Job | None:
    job = await get_job(job_id)
    if not job:
        return None

    for k, v in kwargs.items():
        setattr(job, k, v)
    job.touch()

    repo = get_repository()
    updated = await repo.update(
        job_id,
        status=job.status,
        result=job.result,
        error=job.error,
        progress=job.progress,
    )

    if updated and job.status in (
        JobStatus.DONE,
        JobStatus.ERROR,
        JobStatus.CANCELLED,
    ):
        _active_cache.pop(job_id, None)
    elif updated:
        _active_cache[job_id] = updated

    return updated


async def add_progress(job_id: str, message: str, step: int | None = None) -> None:
    job = await get_job(job_id)
    if not job:
        return
    job.progress.append(ProgressEvent(message=message, step=step))
    job.touch()
    await get_repository().update(job_id, progress=job.progress)
    _active_cache[job_id] = job


async def get_stats() -> dict:
    return await get_repository().get_stats()


async def cancel_job(job_id: str) -> Job | None:
    job = await get_job(job_id)
    if not job:
        return None

    if job.status in (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED):
        return job

    request_cancel(job_id)
    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()

    await add_progress(job_id, "Cancelado pelo usuário", None)
    return await update_job(
        job_id,
        status=JobStatus.CANCELLED,
        error="Cancelado pelo usuário",
    )


async def delete_job(job_id: str) -> bool:
    job = await get_job(job_id)
    if not job:
        return False

    if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
        await cancel_job(job_id)

    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
    unregister_running_task(job_id)
    clear_cancel(job_id)
    _active_cache.pop(job_id, None)

    return await get_repository().delete(job_id)
