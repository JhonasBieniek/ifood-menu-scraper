# Imagem com Camoufox (Firefox) para scraping DOM + interceptação de rede.

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

ENV SCRAPER_STRATEGY=auto
ENV PORT=3001
ENV HOST=0.0.0.0

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3001/api/health')"

CMD ["python", "main.py"]
