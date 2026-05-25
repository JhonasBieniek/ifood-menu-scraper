"""Testes do repositório SQLite."""

import pytest

from src.db.repository import get_repository
from src.jobs.models import JobStatus
from src.jobs.store import (
    add_progress,
    cancel_job,
    create_job,
    delete_job,
    get_job,
    update_job,
)


@pytest.mark.asyncio
async def test_create_and_get_job(test_db, sample_ifood_url):
    job = await create_job(sample_ifood_url)
    assert job.id
    assert job.url == sample_ifood_url
    assert job.status == JobStatus.PENDING

    loaded = await get_job(job.id)
    assert loaded is not None
    assert loaded.id == job.id


@pytest.mark.asyncio
async def test_update_job_with_result(test_db, sample_ifood_url):
    job = await create_job(sample_ifood_url)
    result = {"name": "Loja Teste", "categories": []}
    await update_job(job.id, status=JobStatus.DONE, result=result)

    loaded = await get_job(job.id)
    assert loaded.status == JobStatus.DONE
    assert loaded.result == result


@pytest.mark.asyncio
async def test_append_progress(test_db, sample_ifood_url):
    job = await create_job(sample_ifood_url)
    await add_progress(job.id, "Abrindo página", 1)
    await add_progress(job.id, "Extraindo cardápio", 2)

    loaded = await get_job(job.id)
    assert len(loaded.progress) == 2
    assert loaded.progress[0].message == "Abrindo página"


@pytest.mark.asyncio
async def test_list_history_pagination(test_db, sample_ifood_url):
    for i in range(3):
        j = await create_job(f"{sample_ifood_url}?n={i}")
        await update_job(
            j.id,
            status=JobStatus.DONE,
            result={"name": f"Loja {i}", "categories": []},
        )

    repo = get_repository()
    page = await repo.list_history(limit=2, offset=0)
    assert page.total == 3
    assert len(page.items) == 2
    assert page.items[0].store_name == "Loja 2"

    page2 = await repo.list_history(limit=2, offset=2)
    assert len(page2.items) == 1


@pytest.mark.asyncio
async def test_list_history_filter_status(test_db, sample_ifood_url):
    ok = await create_job(sample_ifood_url)
    await update_job(ok.id, status=JobStatus.DONE, result={"name": "OK"})

    fail = await create_job(sample_ifood_url + "?err=1")
    await update_job(fail.id, status=JobStatus.ERROR, error="falhou")

    repo = get_repository()
    done_only = await repo.list_history(status=JobStatus.DONE)
    assert done_only.total == 1
    assert done_only.items[0].status == "done"


@pytest.mark.asyncio
async def test_cancel_job(test_db, sample_ifood_url):
    job = await create_job(sample_ifood_url)
    await update_job(job.id, status=JobStatus.RUNNING)

    cancelled = await cancel_job(job.id)
    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.error == "Cancelado pelo usuário"

    loaded = await get_job(job.id)
    assert loaded.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_delete_job(test_db, sample_ifood_url):
    job = await create_job(sample_ifood_url)
    await update_job(job.id, status=JobStatus.DONE, result={"name": "X"})

    assert await delete_job(job.id) is True
    assert await get_job(job.id) is None
    assert await get_repository().delete(job.id) is False


@pytest.mark.asyncio
async def test_get_stats(test_db, sample_ifood_url):
    j = await create_job(sample_ifood_url)
    await update_job(j.id, status=JobStatus.RUNNING)

    stats = await get_repository().get_stats()
    assert stats["total"] >= 1
    assert stats["running"] >= 1
