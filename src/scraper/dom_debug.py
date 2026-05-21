"""
Diagnóstico da extração DOM (contagens, amostras, screenshot).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Page

DEBUG_DIR = Path(__file__).resolve().parents[2] / ".debug"


def format_debug_summary(debug: dict[str, Any]) -> str:
    if not debug:
        return ""
    parts = [
        f"titulo={debug.get('pageTitle', '?')!r}",
        f"categorias={debug.get('categoryCount', debug.get('menuGroupCount', 0))}",
        f"cards_extraidos={debug.get('totalCards', 0)}",
        f"nome_loja={debug.get('storeName')!r}",
    ]
    names = debug.get("categoryNames") or []
    if names:
        parts.append("secoes=" + ", ".join(names[:8]))
    hits = debug.get("selectorHits") or {}
    if hits:
        parts.append(
            "dom="
            + ", ".join(f"{k}:{v}" for k, v in hits.items())
        )
    samples = debug.get("samplePriceTexts") or []
    if samples:
        parts.append("amostra_precos=" + " | ".join(samples[:3]))
    if debug.get("screenshotPath"):
        parts.append(f"screenshot={debug['screenshotPath']}")
    return "; ".join(parts)


async def collect_dom_diagnostics(page: Page, merchant_id: str) -> dict[str, Any]:
    from .dom_selectors import DOM_DIAGNOSTIC_SCRIPT

    diag = await page.evaluate(DOM_DIAGNOSTIC_SCRIPT, merchant_id)
    return diag if isinstance(diag, dict) else {}


async def maybe_save_screenshot(page: Page, merchant_id: str, label: str) -> str | None:
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = DEBUG_DIR / f"{merchant_id[:8]}_{label}_{ts}.png"
        await page.screenshot(path=str(path), full_page=False)
        return str(path)
    except Exception:
        return None


def merge_debug_into_error(message: str, debug: dict[str, Any]) -> str:
    summary = format_debug_summary(debug)
    if summary:
        return f"{message} | {summary}"
    return message
