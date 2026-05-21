"""
Normaliza dados extraídos do DOM para o mesmo schema do parser de API.
"""

from __future__ import annotations

import re
from datetime import datetime

from .images import build_header_url, build_logo_url, build_product_image_url

PRICE_RE = re.compile(
    r"(?:R\$\s*|r\$\s*|(?:a partir de|apartir de)\s*)([\d.,]+)",
    re.IGNORECASE,
)
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def parse_price_text(price_text: str) -> int:
    """Converte 'R$ 24,99', '+ R$ 2,50' ou 'R$ 1.234,56' para centavos."""
    if not price_text:
        return 0
    cleaned = re.sub(r"^\+\s*", "", price_text.replace("\xa0", " ").strip())
    m = PRICE_RE.search(cleaned)
    if not m:
        return 0
    raw = m.group(1).strip()
    if "," in raw:
        parts = raw.replace(".", "").split(",")
        reais = int(parts[0]) if parts[0] else 0
        cents = int((parts[1] + "00")[:2]) if len(parts) > 1 else 0
        return reais * 100 + cents
    if "." in raw:
        return round(float(raw) * 100)
    return int(raw) * 100


PRATO_RE = re.compile(r"[?&]prato=([0-9a-f-]{36})", re.IGNORECASE)


def _normalize_product_image_url(src: str | None, merchant_id: str) -> str | None:
    if not src:
        return None
    if src.startswith("http"):
        url = src.split("?")[0]
        return (
            url.replace("/t_low/", "/t_high/")
            .replace("/t_thumbnail/", "/t_high/")
            .replace("/t_medium/", "/t_high/")
        )
    path = _image_path_from_src(src, merchant_id)
    return build_product_image_url(path, merchant_id) if path else None


def _image_path_from_src(src: str | None, merchant_id: str) -> str | None:
    if not src:
        return None
    if "pratos/" in src:
        idx = src.find("pratos/")
        return src[idx + len("pratos/") :].split("?")[0]
    if merchant_id in src:
        idx = src.find(merchant_id)
        return src[idx:].split("?")[0]
    um = UUID_RE.search(src)
    if um:
        tail = src[um.start() :].split("?")[0]
        if "/" in tail:
            return tail
    return None


def _logo_path_from_src(src: str | None) -> str | None:
    if not src:
        return None
    if "logosgde/" in src:
        return src.split("logosgde/")[-1].split("?")[0]
    if "/image/upload/" in src:
        return src.split("/image/upload/")[-1].split("?")[0]
    return src.split("?")[0] if src.startswith("http") else src


def _cover_path_from_src(src: str | None) -> str | None:
    if not src:
        return None
    if "capa/" in src:
        return src.split("capa/")[-1].split("?")[0]
    if "/image/upload/" in src:
        return src.split("/image/upload/")[-1].split("?")[0]
    return src.split("?")[0] if src.startswith("http") else src


def parse_dom_item(raw: dict, merchant_id: str) -> dict:
    price = parse_price_text(raw.get("priceText") or "")
    href = raw.get("href") or ""
    prato_m = PRATO_RE.search(href)
    item_id = raw.get("id") or (prato_m.group(1) if prato_m else None)
    if not item_id:
        item_id = f"dom-{hash(raw.get('name', ''))}"
    description = (raw.get("detailsText") or "").strip() or None

    complement_groups = []
    for g in raw.get("complementGroups") or []:
        options = []
        for o in g.get("options") or []:
            name = (o.get("name") or "").strip()
            if not name:
                continue
            opt_id = (o.get("id") or "").strip() or f"opt-{hash(name)}"
            options.append(
                {
                    "id": opt_id,
                    "name": name,
                    "description": None,
                    "price": parse_price_text(o.get("priceText") or ""),
                    "available": True,
                    "image_url": None,
                }
            )
        if not options:
            continue
        complement_groups.append(
            {
                "id": f"grp-{hash(g.get('name', ''))}",
                "name": (g.get("name") or "Complemento").strip(),
                "min": 0,
                "max": len(options),
                "required": False,
                "options": options,
            }
        )

    return {
        "id": item_id,
        "name": (raw.get("name") or "").strip(),
        "description": description,
        "price": price,
        "original_price": None,
        "discount": None,
        "image_url": _normalize_product_image_url(raw.get("imageSrc"), merchant_id),
        "available": True,
        "serves": None,
        "complement_groups": complement_groups,
    }


def build_catalog_from_dom(
    dom_data: dict,
    merchant_id: str,
    source_url: str,
    *,
    items_detail_fetched: int = 0,
    items_detail_skipped: int = 0,
) -> dict:
    store = dom_data.get("store") or {}
    logo_path = _logo_path_from_src(store.get("logoSrc"))
    cover_path = _cover_path_from_src(store.get("coverSrc"))

    categories = []
    for i, cat in enumerate(dom_data.get("categories") or []):
        items = [
            parse_dom_item(it, merchant_id)
            for it in (cat.get("items") or [])
            if (it.get("name") or "").strip()
        ]
        if not items:
            continue
        cat_id = (cat.get("id") or f"cat-{i}").strip()
        categories.append(
            {
                "id": cat_id,
                "name": (cat.get("name") or f"Categoria {i + 1}").strip(),
                "description": None,
                "sort_order": i,
                "items": items,
            }
        )

    total_items = sum(len(c["items"]) for c in categories)
    items_with_complements = sum(
        1 for c in categories for it in c["items"] if it["complement_groups"]
    )

    return {
        "external_id": merchant_id,
        "name": (store.get("name") or "").strip() or None,
        "description": None,
        "logo_url": build_logo_url(logo_path) if logo_path else None,
        "cover_url": build_header_url(cover_path) if cover_path else None,
        "address": None,
        "categories": categories,
        "meta": {
            "total_categories": len(categories),
            "total_items": total_items,
            "items_with_complements": items_with_complements,
            "data_source": "dom_ui",
            "items_detail_fetched": items_detail_fetched,
            "items_detail_skipped": items_detail_skipped,
            "scraped_at": datetime.now().isoformat(),
            "source_url": source_url,
        },
    }
