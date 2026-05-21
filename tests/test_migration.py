"""Testes do pipeline compartilhado de migracao."""

from src.scraper.migration import (
    ScrapeOptions,
    format_migration_summary,
    normalize_strategy,
)


def test_normalize_strategy_legacy_aliases():
    assert normalize_strategy("camoufox") == "network"
    assert normalize_strategy("curl") == "auto"
    assert normalize_strategy("DOM") == "dom"


def test_scrape_options_from_config():
    opts = ScrapeOptions.from_config(strategy="dom")
    assert opts.strategy == "dom"
    assert opts.timeout_s is not None
    assert opts.max_items_detail is not None


def test_format_migration_summary():
    result = {
        "external_id": "abc",
        "name": "Loja",
        "meta": {"total_items": 2, "total_categories": 1},
        "categories": [
            {
                "id": "menu-group-1",
                "name": "Combos",
                "items": [
                    {"complement_groups": [{"name": "Adicionais"}]},
                    {"complement_groups": []},
                ],
            }
        ],
    }
    summary = format_migration_summary(result)
    assert summary["store_name"] == "Loja"
    assert summary["categories"][0]["item_count"] == 2
    assert summary["categories"][0]["items_with_complements"] == 1
