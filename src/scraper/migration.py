"""
Ponto de entrada unico para migracao iFood (API, CLI debug, testes).

Toda execucao passa por `run_migration` com `ScrapeOptions` derivado do config
ou sobrescrito explicitamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from src.config import config
from src.scraper.resolver import extract_merchant_id_or_raise
from src.scraper.strategy_dom import DomScrapeError, scrape_with_dom
from src.scraper.strategy_network import scrape_with_network

ProgressCallback = Callable[[str, int | None], Awaitable[None]]

_LEGACY_STRATEGY_ALIASES = {"camoufox": "network", "curl": "auto"}


@dataclass
class ScrapeOptions:
    """Parametros de uma execucao de migracao."""

    strategy: str | None = None
    timeout_s: int | None = None
    max_items_detail: int | None = None

    @classmethod
    def from_config(cls, *, strategy: str | None = None) -> ScrapeOptions:
        return cls(
            strategy=strategy or config.SCRAPER_STRATEGY,
            timeout_s=config.SCRAPE_TIMEOUT_S,
            max_items_detail=config.MAX_ITEMS_DETAIL,
        )


def normalize_strategy(strategy: str) -> str:
    key = (strategy or "auto").lower().strip()
    return _LEGACY_STRATEGY_ALIASES.get(key, key)


async def _noop_progress(_message: str, _step: int | None = None) -> None:
    pass


async def run_migration(
    url: str,
    on_progress: ProgressCallback | None = None,
    options: ScrapeOptions | None = None,
) -> dict:
    """
    Executa migracao conforme estrategia (dom | network | auto).

    Usado pela API (`migrate.py`), pelo CLI `scripts/debug_dom.py` e testes.
    """
    opts = options or ScrapeOptions.from_config()
    merchant_id = extract_merchant_id_or_raise(url)
    strategy = normalize_strategy(opts.strategy or "auto")
    timeout_s = opts.timeout_s if opts.timeout_s is not None else config.SCRAPE_TIMEOUT_S
    progress = on_progress or _noop_progress

    dom_kwargs = {
        "max_items_detail": opts.max_items_detail,
    }

    if strategy == "dom":
        return await scrape_with_dom(
            merchant_id, url, progress, timeout_s, **dom_kwargs
        )

    if strategy == "network":
        return await scrape_with_network(merchant_id, url, progress, timeout_s)

    # auto: DOM primeiro, fallback network
    try:
        await progress("Tentando migracao pela interface (DOM)...", 1)
        return await scrape_with_dom(
            merchant_id, url, progress, timeout_s, **dom_kwargs
        )
    except DomScrapeError as exc:
        detail = str(exc).strip() or "falha desconhecida no DOM"
        await progress(
            f"DOM insuficiente. Ativando fallback por rede... ({detail})",
            2,
        )
        return await scrape_with_network(merchant_id, url, progress, timeout_s)


def format_migration_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Resumo legivel para logs/CLI (sem dump completo do cardapio)."""
    meta = result.get("meta") or {}
    categories = result.get("categories") or []
    return {
        "meta": meta,
        "external_id": result.get("external_id"),
        "store_name": result.get("name"),
        "logo_url": result.get("logo_url"),
        "cover_url": result.get("cover_url"),
        "categories": [
            {
                "id": cat.get("id"),
                "name": cat.get("name"),
                "item_count": len(cat.get("items") or []),
                "items_with_complements": sum(
                    1
                    for it in (cat.get("items") or [])
                    if it.get("complement_groups")
                ),
            }
            for cat in categories
        ],
    }


__all__ = [
    "DomScrapeError",
    "ProgressCallback",
    "ScrapeOptions",
    "format_migration_summary",
    "normalize_strategy",
    "run_migration",
]
