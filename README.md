# ifood-migrator-py

Extrator de cardápio iFood com interface web local, API REST assíncrona e histórico em SQLite.

## Requisitos

- Python 3.11+
- Camoufox (Firefox) — baixado na primeira execução

## Instalação local

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "from camoufox.sync_api import Camoufox; Camoufox.fetch()"
cp .env.example .env
```

Edite `.env` conforme necessário (porta, estratégia de scraping, API key).

## Executar

```bash
python main.py
```

- **Interface web:** http://localhost:3005/ (ou a porta definida em `PORT`)
- **OpenAPI:** http://localhost:3005/docs

## Interface web

1. Cole a URL completa da loja no iFood (`https://www.ifood.com.br/delivery/.../{uuid}`)
2. Clique em **Iniciar migração**
3. Acompanhe o progresso e visualize/baixe o JSON do cardápio
4. Consulte o **histórico** de scrapings anteriores na mesma página

## API REST (assíncrona)

### Iniciar scraping

```http
POST /api/migrate
Content-Type: application/json
X-Api-Key: <sua-chave>   # se API_KEY estiver definida no .env

{ "url": "https://www.ifood.com.br/delivery/cidade/loja/uuid" }
```

Resposta `202`:

```json
{
  "job_id": "...",
  "status": "pending",
  "status_url": "/api/migrate/{id}",
  "events_url": "/api/migrate/{id}/events"
}
```

### Polling do resultado

```http
GET /api/migrate/{job_id}
X-Api-Key: <sua-chave>
```

Repita até `status` ser `done`, `error` ou `cancelled`. O campo `result` contém o JSON do cardápio.

### Cancelar consulta em andamento

```http
POST /api/migrate/{job_id}/cancel
X-Api-Key: <sua-chave>
```

### Histórico

```http
GET /api/scrapes?limit=20&offset=0&status=done
GET /api/scrapes/{job_id}
DELETE /api/scrapes/{job_id}
```

`DELETE` remove o registro do SQLite. Se o job ainda estiver `pending` ou `running`, ele é cancelado antes da exclusão.

### Health

```http
GET /api/health
```

## Expor via ngrok (requisições externas)

**Recomendado:** defina `API_KEY` no `.env` antes de expor.

```bash
# Terminal 1 — servidor local
python main.py

# Terminal 2 — túnel (ajuste a porta se necessário)
ngrok http 3005
```

Cliente externo:

```bash
curl -X POST "https://SEU_SUBDOMINIO.ngrok-free.app/api/migrate" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: SUA_CHAVE" \
  -d '{"url":"https://www.ifood.com.br/delivery/..."}'

# Polling
curl -H "X-Api-Key: SUA_CHAVE" \
  "https://SEU_SUBDOMINIO.ngrok-free.app/api/migrate/JOB_ID"
```

O scraping pode levar até `SCRAPE_TIMEOUT_S` segundos (padrão: 60).

## Banco de dados

Histórico persistido em SQLite (`DATABASE_PATH`, padrão `./data/scraper.db`). A pasta `data/` não é versionada no Git.

## Docker (opcional)

```bash
docker compose up --build
```

## Testes

```bash
pytest -q
```
