"""
Estratégia DOM Pure UI: lê o que é renderizado na página (sem interceptar API).
"""

from __future__ import annotations

import asyncio
import time

from playwright.async_api import Page

from src.config import config
from .browser import (
    dismiss_cookie_banner,
    dismiss_location_modal,
    open_camoufox_page,
    trigger_lazy_scroll,
)
from .dom_debug import (
    collect_dom_diagnostics,
    format_debug_summary,
    maybe_save_screenshot,
    merge_debug_into_error,
)
from .dom_parser import build_catalog_from_dom
from .dom_selectors import (
    EXTRACT_MODAL_GROUPS_JS,
    EXTRACT_VISIBLE_MENU_SCRIPT,
    PRODUCT_CARD,
    PRODUCT_MODAL,
)


class DomScrapeError(Exception):
    """Falha na extração DOM — orquestrador pode tentar fallback network."""

    def __init__(self, message: str, debug: dict | None = None):
        super().__init__(message)
        self.debug = debug or {}


async def scrape_with_dom(
    merchant_id: str,
    source_url: str,
    on_progress=None,
    timeout_s: int = 60,
    *,
    max_items_detail: int | None = None,
) -> dict:
    max_detail = (
        max_items_detail
        if max_items_detail is not None
        else config.MAX_ITEMS_DETAIL
    )
    last_debug: dict = {}

    if on_progress:
        await on_progress("Iniciando Camoufox (estrategia DOM / UI)...", 1)

    async with open_camoufox_page(block_media=False) as page:
        if on_progress:
            await on_progress("Acessando pagina da loja no iFood...", 2)

        try:
            await page.goto(
                source_url,
                wait_until="load",
                timeout=timeout_s * 1000,
            )
        except Exception:
            await page.goto(
                source_url,
                wait_until="domcontentloaded",
                timeout=timeout_s * 1000,
            )

        await dismiss_cookie_banner(page)
        await dismiss_location_modal(page)
        await asyncio.sleep(1.5)

        if on_progress:
            await on_progress("Aguardando cardapio visivel na tela...", 3)

        await _wait_for_menu(page, merchant_id, timeout_s, on_progress)

        if on_progress:
            await on_progress("Rolando pagina para carregar todos os produtos...", 3)

        await trigger_lazy_scroll(page)
        dom_data = await _extract_with_scroll_stability(page, merchant_id)
        last_debug = dom_data.get("debug") or {}

        if on_progress and last_debug:
            await on_progress(
                f"DOM scan: {format_debug_summary({**last_debug, 'totalCards': dom_data.get('totalCards', 0)})}",
                3,
            )

        detail_fetched = 0
        detail_skipped = 0
        probe_items = _items_for_detail_probe(dom_data, max_detail)

        if probe_items and max_detail > 0 and on_progress:
            await on_progress(
                f"Consultando complementos em ate {len(probe_items)} produto(s)...",
                4,
            )

        for item in probe_items:
            if detail_fetched >= max_detail:
                break
            groups = await _fetch_complements_from_modal(page, item, timeout_s)
            if groups:
                item["complementGroups"] = groups
                detail_fetched += 1
            else:
                detail_skipped += 1
            await asyncio.sleep(0.2)

        if on_progress:
            await on_progress("Processando dados capturados da interface...", 5)

        result = build_catalog_from_dom(
            dom_data,
            merchant_id,
            source_url,
            items_detail_fetched=detail_fetched,
            items_detail_skipped=detail_skipped,
        )

        if result["meta"]["total_items"] == 0 or not (result.get("name") or "").strip():
            if config.SCRAPER_DEBUG:
                shot = await maybe_save_screenshot(page, merchant_id, "dom_fail")
                if shot:
                    last_debug["screenshotPath"] = shot
            diag = await collect_dom_diagnostics(page, merchant_id)
            last_debug = {**last_debug, **diag}

        if not (result.get("name") or "").strip():
            raise DomScrapeError(
                merge_debug_into_error("Nome da loja nao encontrado na pagina.", last_debug),
                debug=last_debug,
            )

        if result["meta"]["total_items"] == 0:
            raise DomScrapeError(
                merge_debug_into_error(
                    "Nenhum produto visivel encontrado no cardapio.",
                    {**last_debug, "totalCards": 0},
                ),
                debug=last_debug,
            )

        if on_progress:
            await on_progress(
                f"Concluido (DOM): {result['meta']['total_categories']} categorias, "
                f"{result['meta']['total_items']} produtos",
                6,
            )

        return result


async def _wait_for_menu(
    page: Page, merchant_id: str, timeout_s: int, on_progress=None
) -> None:
    deadline = time.monotonic() + min(timeout_s * 0.55, 35)

    while time.monotonic() < deadline:
        diag = await collect_dom_diagnostics(page, "")
        prices = diag.get("priceMatches") or 0
        card_count = 0
        for sel in PRODUCT_CARD[:8]:
            try:
                card_count += await page.locator(sel).count()
            except Exception:
                pass

        groups = diag.get("menuGroupCount") or 0
        dish_cards = diag.get("dishCardCount") or 0
        if (groups >= 1 and dish_cards >= 2) or card_count >= 2 or prices >= 2:
            if on_progress:
                await on_progress(
                    f"Cardapio detectado: {groups} secoes, {dish_cards} pratos, {prices} precos",
                    3,
                )
            return

        await asyncio.sleep(0.6)

    diag = await collect_dom_diagnostics(page, merchant_id)
    if config.SCRAPER_DEBUG:
        await maybe_save_screenshot(page, merchant_id, "menu_wait")

    raise DomScrapeError(
        merge_debug_into_error(
            "Cardapio nao apareceu na pagina dentro do tempo limite.",
            {**diag, "totalCards": 0},
        ),
        debug=diag,
    )


async def _extract_with_scroll_stability(page: Page, merchant_id: str) -> dict:
    last_count = -1
    stable = 0
    best = None

    for _ in range(8):
        data = await page.evaluate(EXTRACT_VISIBLE_MENU_SCRIPT, merchant_id)
        if data.get("debug"):
            data["debug"]["totalCards"] = data.get("totalCards", 0)

        count = data.get("totalCards") or 0
        if count >= last_count:
            best = data
        if count == last_count and count > 0:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last_count = count
        await trigger_lazy_scroll(page, steps=4)

    if not best:
        best = await page.evaluate(EXTRACT_VISIBLE_MENU_SCRIPT, merchant_id)
    return best


def _items_for_detail_probe(dom_data: dict, max_with_complements: int) -> list[dict]:
    """Ordena candidatos (combos/descrição primeiro) e limita tentativas de abertura."""
    items: list[dict] = []
    for cat in dom_data.get("categories") or []:
        for item in cat.get("items") or []:
            if item.get("id"):
                items.append(item)

    def sort_key(it: dict) -> tuple:
        name = (it.get("name") or "").lower()
        has_details = 0 if (it.get("detailsText") or "").strip() else 1
        is_combo = 0 if "combo" in name or "x-" in name or "burger" in name else 1
        return (has_details, is_combo, name)

    items.sort(key=sort_key)
    max_probe = min(len(items), max(15, max_with_complements * 8))
    return items[:max_probe]


async def _fetch_complements_from_modal(
    page: Page,
    item: dict,
    timeout_s: int,
) -> list[dict]:
    name = item.get("name") or ""
    if not name:
        return []

    clicked = await _click_product_card(page, item)
    if not clicked:
        return []

    try:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        garnish_found = False
        for sel in (
            ".dish-garnishes",
            ".garnish-choices__label",
            ".garnish-choices__list",
            *PRODUCT_MODAL,
        ):
            try:
                await page.locator(sel).first.wait_for(state="visible", timeout=8000)
                garnish_found = True
                break
            except Exception:
                continue

        await asyncio.sleep(0.8 if garnish_found else 0.4)
        groups = await page.evaluate(EXTRACT_MODAL_GROUPS_JS)
        if not groups:
            await asyncio.sleep(0.6)
            groups = await page.evaluate(EXTRACT_MODAL_GROUPS_JS)
        return groups if isinstance(groups, list) else []
    finally:
        await _close_product_view(page)


async def _click_product_card(page: Page, item: dict) -> bool:
    product_name = item.get("name") or ""
    prato_id = item.get("id") or ""
    if prato_id and len(prato_id) >= 32:
        try:
            link = page.locator(f'a.dish-card[href*="prato={prato_id}"]').first
            if await link.count() > 0:
                await link.scroll_into_view_if_needed(timeout=5000)
                await link.click(timeout=8000)
                return True
        except Exception:
            pass

    for sel in PRODUCT_CARD:
        try:
            card = page.locator(sel).filter(has_text=product_name).first
            if await card.count() > 0:
                await card.click(timeout=5000)
                return True
        except Exception:
            continue

    try:
        return await page.evaluate(
            """(name) => {
              const cards = document.querySelectorAll('a.dish-card');
              for (const c of cards) {
                if ((c.textContent || '').includes(name)) {
                  c.click();
                  return true;
                }
              }
              return false;
            }""",
            product_name,
        )
    except Exception:
        return False


async def _close_product_view(page: Page) -> None:
    """Volta ao cardapio apos pagina/modal do prato (?prato=)."""
    url = page.url or ""
    if "prato=" in url:
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=12000)
            await asyncio.sleep(0.6)
            return
        except Exception:
            pass

    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
    except Exception:
        pass
    for sel in (
        'button[aria-label*="fechar" i]',
        '[data-test-id="modal-close"]',
        '[data-testid="modal-close"]',
    ):
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=800):
                await btn.click(timeout=2000)
                return
        except Exception:
            continue
