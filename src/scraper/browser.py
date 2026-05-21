"""
Camoufox compartilhado: factory de browser/page e helpers de navegação.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Browser, Page, Route

COOKIE_BANNER_SELECTORS = [
    'button:has-text("Aceitar")',
    'button:has-text("Aceitar todos")',
    'button:has-text("Concordo")',
    '[data-testid="cookie-banner-accept"]',
    "#onetrust-accept-btn-handler",
]

LOCATION_MODAL_SELECTORS = [
    'button:has-text("Continuar")',
    'button:has-text("Agora não")',
    'button:has-text("Depois")',
    'button:has-text("Ignorar")',
    '[data-testid="location-denied-button"]',
]

TRACKER_URL_FRAGMENTS = ("gtm.js", "analytics", "hotjar", "clarity", "segment", "mixpanel")


@asynccontextmanager
async def open_camoufox_browser() -> AsyncIterator[Browser]:
    async with AsyncCamoufox(
        headless=True,
        geoip=True,
        locale="pt-BR",
    ) as browser:
        yield browser


@asynccontextmanager
async def open_camoufox_page(block_media: bool = False) -> AsyncIterator[Page]:
    async with open_camoufox_browser() as browser:
        page = await browser.new_page()
        if block_media:
            await page.route("**/*", _route_block_heavy)
        else:
            await page.route("**/*", _route_block_trackers_only)
        try:
            yield page
        finally:
            await page.close()


async def _route_block_trackers_only(route: Route) -> None:
    url = route.request.url
    if any(t in url for t in TRACKER_URL_FRAGMENTS):
        await route.abort()
    else:
        await route.continue_()


async def _route_block_heavy(route: Route) -> None:
    if route.request.resource_type in ("image", "media", "font"):
        await route.abort()
    elif any(t in route.request.url for t in TRACKER_URL_FRAGMENTS):
        await route.abort()
    else:
        await route.continue_()


async def dismiss_cookie_banner(page: Page) -> None:
    for selector in COOKIE_BANNER_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1500):
                await btn.click(timeout=3000)
                await asyncio.sleep(0.5)
                return
        except Exception:
            continue


async def dismiss_location_modal(page: Page) -> None:
    for selector in LOCATION_MODAL_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1200):
                await btn.click(timeout=3000)
                await asyncio.sleep(0.5)
                return
        except Exception:
            continue


async def trigger_lazy_scroll(page: Page, steps: int = 5) -> None:
    height = await page.evaluate("document.body.scrollHeight")
    for i in range(1, steps + 1):
        await page.evaluate(f"window.scrollTo(0, {int(height * i / steps)})")
        await asyncio.sleep(0.7)
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(1)
