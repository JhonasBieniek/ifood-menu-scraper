# iFood Migrator

Ferramenta para **extrair o cardápio completo de uma loja no iFood** e exportar em JSON estruturado — via interface web ou API REST assíncrona.

Scraping resiliente com browser headless, jobs em background, histórico persistido e documentação integrada para quem consome a API.

> Uso educacional e de integração própria. Não é produto oficial do iFood.

## O que faz

- URL da loja (`ifood.com.br/delivery/...`) → **Camoufox** → JSON (categorias, itens, preços, complementos) + histórico em SQLite

| `SCRAPER_STRATEGY` | Comportamento |
|--------|----------------|
| `auto` | DOM primeiro; fallback rede (padrão) |
| `dom` | UI renderizada + modais de produto |
| `network` | APIs internas (catálogo / merchant) |

**Stack:** Python 3.11+ · FastAPI · Camoufox · aiosqlite · UI estática (pt-BR / English)

## Rodar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "from camoufox.sync_api import Camoufox; Camoufox.fetch()"
cp .env.example .env
python main.py
```

**Docker (opcional):** `docker compose up --build` — mesmo `.env`; SQLite em `./data` (volume). No container: `HOST=0.0.0.0`, `DATABASE_PATH=/app/data/scraper.db`.

| Recurso | URL |
|---------|-----|
| Interface web | http://localhost:3005/ |
| OpenAPI | http://localhost:3005/docs |

Na UI: URL → **Iniciar migração** → progresso (SSE) → copiar/baixar JSON. Endpoints na aba **API e uso**; idioma no cabeçalho.

## API

Fluxo: **criar job → SSE ou polling → `result` com `status=done`**.

```http
POST /api/migrate
{ "url": "https://www.ifood.com.br/delivery/cidade/loja/uuid" }
```

`202` → `job_id`, `status_url`, `events_url`, `cancel_url`.

Detalhes e cURL: aba API na UI ou `/docs`. `API_KEY` vazio = sem auth (só local); ao expor na rede, defina chave.

## Visão técnica

Jobs assíncronos (concorrência + cancelamento) · progresso via **SSE (Server-Sent Events)** · SQLite · API key opcional · estratégia DOM + rede
