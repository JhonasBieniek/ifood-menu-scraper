"""Testes das rotas de histórico e migração (HTTP)."""

import pytest
from httpx import ASGITransport, AsyncClient

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import config
from src.db.database import close_db, init_db
from src.routes.history import router as history_router
from src.routes.migrate import router as migrate_router


@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def _build_test_app() -> FastAPI:
    test_app = FastAPI(lifespan=_test_lifespan)
    test_app.include_router(migrate_router, prefix="/api")
    test_app.include_router(history_router, prefix="/api")
    return test_app


app = _build_test_app()

SAMPLE_URL = (
    "https://www.ifood.com.br/delivery/londrina-pr/loja-teste/"
    "eb040eab-e24a-4ded-a4b0-421f1629d3b1"
)


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "routes_test.db"
    monkeypatch.setattr(config, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(config, "API_KEY", "test-secret")
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await close_db()


def auth_headers():
    return {"X-Api-Key": "test-secret"}


@pytest.mark.asyncio
async def test_health_includes_database(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["database"] == "ok"


@pytest.mark.asyncio
async def test_migrate_rejects_invalid_url(client):
    res = await client.post(
        "/api/migrate",
        json={"url": "https://example.com/loja"},
        headers=auth_headers(),
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_migrate_requires_api_key(client):
    res = await client.post(
        "/api/migrate",
        json={"url": SAMPLE_URL},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_scrapes_list_empty(client):
    res = await client.get("/api/scrapes", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_scrapes_detail_not_found(client):
    res = await client.get(
        "/api/scrapes/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(),
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_migrate_accepts_valid_url(client):
    res = await client.post(
        "/api/migrate",
        json={"url": SAMPLE_URL},
        headers=auth_headers(),
    )
    assert res.status_code == 202
    body = res.json()
    assert body["job_id"]
    assert body["status_url"] == f"/api/migrate/{body['job_id']}"
    assert body["events_url"] == f"/api/migrate/{body['job_id']}/events"

    detail = await client.get(
        f"/api/scrapes/{body['job_id']}", headers=auth_headers()
    )
    assert detail.status_code == 200
    assert detail.json()["url"] == SAMPLE_URL
    assert "cancel_url" in body


@pytest.mark.asyncio
async def test_cancel_finished_job_returns_400(client, sample_ifood_url):
    from src.jobs.store import create_job, update_job
    from src.jobs.models import JobStatus

    job = await create_job(sample_ifood_url)
    await update_job(job.id, status=JobStatus.DONE, result={"name": "Ok"})

    res = await client.post(
        f"/api/migrate/{job.id}/cancel",
        headers=auth_headers(),
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_cancel_running_job(client, sample_ifood_url):
    from src.jobs.store import create_job, update_job
    from src.jobs.models import JobStatus

    job = await create_job(sample_ifood_url)
    await update_job(job.id, status=JobStatus.RUNNING)

    res = await client.post(
        f"/api/migrate/{job.id}/cancel",
        headers=auth_headers(),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_delete_scrape(client, sample_ifood_url):
    from src.jobs.store import create_job, update_job
    from src.jobs.models import JobStatus

    job = await create_job(sample_ifood_url)
    await update_job(job.id, status=JobStatus.DONE, result={"name": "Loja"})

    res = await client.delete(f"/api/scrapes/{job.id}", headers=auth_headers())
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    detail = await client.get(f"/api/scrapes/{job.id}", headers=auth_headers())
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_delete_scrape_not_found(client):
    res = await client.delete(
        "/api/scrapes/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(),
    )
    assert res.status_code == 404
