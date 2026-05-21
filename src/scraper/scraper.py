"""
Orquestrador de scraping (facade).

Implementacao em `migration.run_migration`; este modulo mantem compatibilidade
com imports existentes (`scrape_ifood_store`).
"""

from src.scraper.migration import (
    DomScrapeError,
    ProgressCallback,
    ScrapeOptions,
    run_migration,
)

__all__ = [
    "DomScrapeError",
    "ProgressCallback",
    "ScrapeOptions",
    "scrape_ifood_store",
]


async def scrape_ifood_store(
    url: str,
    on_progress: ProgressCallback | None = None,
    *,
    options: ScrapeOptions | None = None,
) -> dict:
    return await run_migration(url, on_progress, options)
