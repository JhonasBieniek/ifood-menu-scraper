# iFood Migrator

Tool to **extract a store's full iFood menu** and export it as structured JSON — via web UI or async REST API.

Resilient scraping with a headless browser, background jobs, persisted history, and built-in docs for API consumers.

> For educational use and your own integrations. Not an official iFood product.

## What it does

- Store URL (`ifood.com.br/delivery/...`) → **Camoufox** → JSON (categories, items, prices, add-ons) + history in SQLite

| `SCRAPER_STRATEGY` | Behavior |
|--------|----------|
| `auto` | DOM first; network fallback (default) |
| `dom` | Rendered UI + product modals |
| `network` | Internal APIs (catalog / merchant) |

**Stack:** Python 3.11+ · FastAPI · Camoufox · aiosqlite · static UI (pt-BR / English)

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "from camoufox.sync_api import Camoufox; Camoufox.fetch()"
cp .env.example .env
python main.py
```

**Docker (optional):** `docker compose up --build` — same `.env`; SQLite in `./data` (volume). In the container: `HOST=0.0.0.0`, `DATABASE_PATH=/app/data/scraper.db`.

| Resource | URL |
|----------|-----|
| Web UI | http://localhost:3005/ |
| OpenAPI | http://localhost:3005/docs |

In the UI: URL → **Start migration** → progress (SSE) → copy/download JSON. Endpoints under the **API & usage** tab; language switcher in the header.

## API

Flow: **create job → SSE or polling → `result` when `status=done`**.

```http
POST /api/migrate
{ "url": "https://www.ifood.com.br/delivery/city/store/uuid" }
```

`202` → `job_id`, `status_url`, `events_url`, `cancel_url`.

Details and cURL examples: API tab in the UI or `/docs`. Empty `API_KEY` = no auth (local only); when exposing on the network, set a key.

## Technical overview

Async jobs (concurrency + cancellation) · progress via **SSE (Server-Sent Events)** · SQLite · optional API key · DOM + network strategy
