import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class ProgressEvent:
    message: str
    step: int | None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Job:
    id: str
    url: str
    status: JobStatus = JobStatus.PENDING
    progress: list[ProgressEvent] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def touch(self):
        self.updated_at = datetime.now().isoformat()


# ─── Store global ────────────────────────────────────────────
_jobs: dict[str, Job] = {}


def create_job(url: str) -> Job:
    job = Job(id=str(uuid.uuid4()), url=url)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> Job | None:
    job = _jobs.get(job_id)
    if not job:
        return None
    for k, v in kwargs.items():
        setattr(job, k, v)
    job.touch()
    return job


def add_progress(job_id: str, message: str, step: int | None = None):
    job = _jobs.get(job_id)
    if job:
        job.progress.append(ProgressEvent(message=message, step=step))
        job.touch()


def get_stats() -> dict:
    counts = {s: 0 for s in JobStatus}
    for j in _jobs.values():
        counts[j.status] += 1
    return {s.value: counts[s] for s in JobStatus} | {"total": len(_jobs)}


# ─── Limpeza automática (TTL 1 hora) ─────────────────────────
async def _cleanup_loop():
    while True:
        await asyncio.sleep(900)  # roda a cada 15 minutos
        cutoff = datetime.now() - timedelta(hours=1)
        expired = [
            jid for jid, j in _jobs.items()
            if j.status in (JobStatus.DONE, JobStatus.ERROR)
            and datetime.fromisoformat(j.created_at) < cutoff
        ]
        for jid in expired:
            del _jobs[jid]
        if expired:
            print(f"[JobStore] {len(expired)} jobs expirados removidos.")


def start_cleanup_task():
    asyncio.create_task(_cleanup_loop())
