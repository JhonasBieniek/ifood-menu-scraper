"""
Estratégia network: intercepta respostas site-api (catalog + merchant-info/graphql).
Fallback quando a extração DOM falha.
"""

import asyncio

from playwright.async_api import Response

from .browser import dismiss_cookie_banner, dismiss_location_modal, open_camoufox_page, trigger_lazy_scroll
from .merchant_info import MERCHANT_GRAPHQL_PATH, is_valid_merchant_info
from .parser import parse_catalog_response

CATALOG_PATH = "/site-api/v1/merchants/restaurant/"
MERCHANT_INFO_WAIT_S = 8


async def scrape_with_network(
    merchant_id: str,
    source_url: str,
    on_progress=None,
    timeout_s: int = 60,
) -> dict:
    if on_progress:
        await on_progress("Iniciando Camoufox (interceptacao de rede)...", 1)

    async with open_camoufox_page(block_media=False) as page:
        captured: dict = {
            "catalog": None,
            "merchant_info": None,
            "error": None,
            "catalog_urls": [],
        }
        catalog_event = asyncio.Event()
        merchant_info_event = asyncio.Event()

        async def handle_response(response: Response):
            if response.status != 200:
                return
            url = response.url
            try:
                if CATALOG_PATH + merchant_id in url and "/catalog" in url:
                    captured["catalog_urls"].append(url)
                    body = await response.json()
                    captured["catalog"] = body
                    catalog_event.set()
                    return

                if MERCHANT_GRAPHQL_PATH in url:
                    body = await response.json()
                    if is_valid_merchant_info(body):
                        captured["merchant_info"] = body
                        merchant_info_event.set()
            except Exception as e:
                if not captured["catalog"]:
                    captured["error"] = str(e) or repr(e)
                    catalog_event.set()

        page.on("response", handle_response)

        if on_progress:
            await on_progress("Acessando a loja no iFood...", 2)

        await page.goto(source_url, wait_until="load", timeout=timeout_s * 1000)
        await dismiss_cookie_banner(page)
        await dismiss_location_modal(page)

        if on_progress:
            await on_progress("Aguardando respostas da API do cardapio...", 3)

        try:
            await asyncio.wait_for(catalog_event.wait(), timeout=timeout_s * 0.5)
        except asyncio.TimeoutError:
            if on_progress:
                await on_progress("Tentando carregar mais dados via scroll...", 3)
            await trigger_lazy_scroll(page)
            try:
                await asyncio.wait_for(catalog_event.wait(), timeout=25)
            except asyncio.TimeoutError:
                urls = ", ".join(captured["catalog_urls"][:3]) or "nenhuma URL /catalog capturada"
                raise RuntimeError(
                    f"Timeout aguardando catalog site-api ({timeout_s}s). URLs vistas: {urls}"
                )

        if not captured["merchant_info"]:
            try:
                await asyncio.wait_for(merchant_info_event.wait(), timeout=MERCHANT_INFO_WAIT_S)
            except asyncio.TimeoutError:
                pass

    if captured["error"]:
        raise RuntimeError(f"Erro ao capturar resposta: {captured['error']}")

    if not captured["catalog"]:
        raise RuntimeError(
            "Nao foi possivel capturar os dados do cardapio via rede. "
            "A loja pode estar fechada ou o iFood alterou os endpoints."
        )

    if on_progress:
        await on_progress("Dados capturados. Processando cardapio...", 4)

    result = parse_catalog_response(
        captured["catalog"],
        merchant_id,
        source_url,
        merchant_info=captured.get("merchant_info"),
    )
    result["meta"]["data_source"] = "network_intercept"

    if result["meta"]["total_items"] == 0:
        raise RuntimeError("Cardapio encontrado mas sem produtos.")

    if on_progress:
        await on_progress(
            f"Concluido (rede): {result['meta']['total_categories']} categorias, "
            f"{result['meta']['total_items']} produtos",
            5,
        )

    return result
