"""
Debug local da migracao (mesmo pipeline da API).

Uso:
  .\\.venv\\Scripts\\python.exe scripts\\debug_dom.py [URL]
  .\\.venv\\Scripts\\python.exe scripts\\debug_dom.py [URL] --strategy dom
  .\\.venv\\Scripts\\python.exe scripts\\debug_dom.py [URL] --full

Usa `run_migration` + `ScrapeOptions` (config/.env), igual a POST /api/migrate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraper.migration import (
    DomScrapeError,
    ScrapeOptions,
    format_migration_summary,
    normalize_strategy,
    run_migration,
)

DEFAULT_URL = (
    "https://www.ifood.com.br/delivery/londrina-pr/"
    "magrelo-lanches-av-sao-joao-antares/"
    "eb040eab-e24a-4ded-a4b0-421f1629d3b1"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug migracao iFood (pipeline compartilhado)")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="URL da loja no iFood")
    parser.add_argument(
        "--strategy",
        default="dom",
        choices=["dom", "network", "auto"],
        help="Estrategia (padrao: dom para isolar UI)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout em segundos (padrao: SCRAPE_TIMEOUT_S do .env)",
    )
    parser.add_argument(
        "--max-detail",
        type=int,
        default=None,
        help="Max produtos com leitura de complementos (padrao: MAX_ITEMS_DETAIL)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Imprime JSON completo do cardapio em vez do resumo",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    opts = ScrapeOptions.from_config(strategy=args.strategy)
    if args.timeout is not None:
        opts.timeout_s = args.timeout
    if args.max_detail is not None:
        opts.max_items_detail = args.max_detail

    strategy = normalize_strategy(opts.strategy or "dom")

    async def progress(msg: str, step: int | None = None) -> None:
        label = step if step is not None else "?"
        print(f"[{label}] {msg}")

    print(
        f"strategy={strategy} timeout_s={opts.timeout_s} "
        f"max_items_detail={opts.max_items_detail}",
        file=sys.stderr,
    )

    try:
        result = await run_migration(args.url, progress, opts)
        if args.full:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(format_migration_summary(result), indent=2, ensure_ascii=False))
        meta = result.get("meta") or {}
        print(
            f"OK: {meta.get('total_items', 0)} produtos, "
            f"{meta.get('total_categories', 0)} categorias, "
            f"complementos={meta.get('items_with_complements', 0)}",
        )
    except DomScrapeError as exc:
        print("DOM ERROR:", exc, file=sys.stderr)
        if exc.debug:
            print("DEBUG:", json.dumps(exc.debug, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
