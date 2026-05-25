"""Repositório SQLite para jobs de scraping."""

from __future__ import annotations  # noqa: I001

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.db.database import get_db
from src.jobs.models import Job, JobStatus, ProgressEvent


@dataclass
class ScrapeListItem:
    id: str
    url: str
    status: str
    created_at: str
    updated_at: str
    store_name: str | None = None


@dataclass
class ScrapeListResult:
    items: list[ScrapeListItem]
    total: int
    limit: int
    offset: int


def _now_iso() -> str:
    return datetime.now().isoformat()


def _row_to_job(row: Any) -> Job:
    progress_raw = row["progress_json"] or "[]"
    progress_data = json.loads(progress_raw)
    progress = [
        ProgressEvent(
            message=p["message"],
            step=p.get("step"),
            timestamp=p.get("timestamp", _now_iso()),
        )
        for p in progress_data
    ]
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return Job(
        id=row["id"],
        url=row["url"],
        status=JobStatus(row["status"]),
        progress=progress,
        result=result,
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _extract_store_name(result_json: str | None) -> str | None:
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
        return data.get("name")
    except (json.JSONDecodeError, TypeError):
        return None


class JobRepository:
    async def create(self, job: Job) -> Job:
        db = get_db()
        await db.execute(
            """
            INSERT INTO scrape_jobs (
                id, url, status, result_json, error, progress_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.url,
                job.status.value,
                None,
                None,
                "[]",
                job.created_at,
                job.updated_at,
            ),
        )
        await db.commit()
        return job

    async def get(self, job_id: str) -> Job | None:
        db = get_db()
        async with db.execute(
            "SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        result: dict | None = None,
        error: str | None = None,
        progress: list[ProgressEvent] | None = None,
    ) -> Job | None:
        job = await self.get(job_id)
        if job is None:
            return None

        if status is not None:
            job.status = status
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if progress is not None:
            job.progress = progress
        job.touch()

        result_json = json.dumps(job.result, ensure_ascii=False) if job.result else None
        progress_json = json.dumps(
            [
                {"message": p.message, "step": p.step, "timestamp": p.timestamp}
                for p in job.progress
            ],
            ensure_ascii=False,
        )

        db = get_db()
        await db.execute(
            """
            UPDATE scrape_jobs SET
                status = ?,
                result_json = ?,
                error = ?,
                progress_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                job.status.value,
                result_json,
                job.error,
                progress_json,
                job.updated_at,
                job_id,
            ),
        )
        await db.commit()
        return job

    async def append_progress(
        self, job_id: str, message: str, step: int | None = None
    ) -> Job | None:
        job = await self.get(job_id)
        if job is None:
            return None
        job.progress.append(ProgressEvent(message=message, step=step))
        job.touch()
        return await self.update(job_id, progress=job.progress)

    async def list_history(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: JobStatus | None = None,
    ) -> ScrapeListResult:
        db = get_db()
        where = ""
        params: list[Any] = []
        if status is not None:
            where = "WHERE status = ?"
            params.append(status.value)

        async with db.execute(
            f"SELECT COUNT(*) AS cnt FROM scrape_jobs {where}", params
        ) as cursor:
            row = await cursor.fetchone()
            total = row["cnt"] if row else 0

        params_list = list(params)
        params_list.extend([limit, offset])
        async with db.execute(
            f"""
            SELECT id, url, status, result_json, created_at, updated_at
            FROM scrape_jobs {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params_list,
        ) as cursor:
            rows = await cursor.fetchall()

        items = [
            ScrapeListItem(
                id=r["id"],
                url=r["url"],
                status=r["status"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                store_name=_extract_store_name(r["result_json"]),
            )
            for r in rows
        ]
        return ScrapeListResult(items=items, total=total, limit=limit, offset=offset)

    async def delete(self, job_id: str) -> bool:
        db = get_db()
        cursor = await db.execute(
            "DELETE FROM scrape_jobs WHERE id = ?", (job_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

    async def get_stats(self) -> dict[str, int]:
        db = get_db()
        counts = {s.value: 0 for s in JobStatus}
        async with db.execute(
            "SELECT status, COUNT(*) AS cnt FROM scrape_jobs GROUP BY status"
        ) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            counts[row["status"]] = row["cnt"]
        total = sum(counts.values())
        return counts | {"total": total}


_repository: JobRepository | None = None


def get_repository() -> JobRepository:
    global _repository
    if _repository is None:
        _repository = JobRepository()
    return _repository
