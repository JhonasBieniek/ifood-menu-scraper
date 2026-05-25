# Imagem com Camoufox (Firefox) para scraping DOM + interceptação de rede.
# Alinhado ao fluxo local: python main.py + variáveis do .env.example

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 \
    libasound2 libpci3 libcurl4 \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from camoufox.sync_api import Camoufox; Camoufox.fetch()"

COPY . .

RUN mkdir -p /app/data

# Mesmos padrões do .env.example (HOST=0.0.0.0 no container para aceitar conexões externas)
ENV HOST=0.0.0.0
ENV PORT=3005
ENV SCRAPER_STRATEGY=auto
ENV DATABASE_PATH=/app/data/scraper.db
ENV MAX_CONCURRENT_JOBS=2
ENV SCRAPE_TIMEOUT_S=60
ENV MAX_ITEMS_DETAIL=40
ENV SCRAPER_DEBUG=true
ENV CORS_ORIGINS=*

EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import os, urllib.request; p=os.getenv('PORT','3005'); urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health', timeout=8)"

CMD ["python", "main.py"]
