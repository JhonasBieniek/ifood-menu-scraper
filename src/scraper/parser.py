"""
Parser: normaliza a resposta da API do iFood para um schema limpo.

O endpoint /site-api/v1/merchants/restaurant/{id}/catalog retorna
um JSON com a estrutura completa do cardápio, incluindo categorias,
itens e grupos de complementos.
"""

from .images import build_header_url, build_logo_url, build_product_image_url


def normalize_price(value) -> int:
    """Converte preço para centavos inteiros."""
    if value is None or value == 0:
        return 0
    value = float(value)
    # Float ou valor < 100 → reais (ex.: 49.90); caso contrário já está em centavos
    if not value.is_integer() or value < 100:
        return round(value * 100)
    return round(value)


# ─── Complementos ─────────────────────────────────────────────

def parse_complement_option(opt: dict, merchant_id: str | None = None) -> dict:
    return {
        "id": opt.get("id") or opt.get("code"),
        "name": (opt.get("description") or opt.get("name") or "").strip(),
        "description": opt.get("details") or None,
        "price": normalize_price(opt.get("unitPrice") or opt.get("price") or 0),
        "available": opt.get("status") == "AVAILABLE" or opt.get("available", True),
        "image_url": build_product_image_url(
            opt.get("imagePath") or opt.get("logoUrl") or opt.get("image"),
            merchant_id,
        ),
    }


def parse_complement_group(group: dict, merchant_id: str | None = None) -> dict | None:
    options = [
        parse_complement_option(o, merchant_id)
        for o in (group.get("options") or group.get("itens") or [])
        if o.get("description") or o.get("name")
    ]
    if not options:
        return None

    min_qty = group.get("min") or group.get("minQuantity") or 0
    max_qty = group.get("max") or group.get("maxQuantity") or len(options)

    return {
        "id": group.get("id") or group.get("code"),
        "name": (group.get("name") or group.get("description") or "Complemento").strip(),
        "min": min_qty,
        "max": max_qty,
        "required": min_qty > 0,
        "options": options,
    }


# ─── Itens ────────────────────────────────────────────────────

def parse_item(item: dict, merchant_id: str | None = None) -> dict:
    price = normalize_price(
        item.get("unitMinPrice")
        or item.get("unitPrice")
        or item.get("price")
        or item.get("minimumPrice")
        or 0
    )
    original_price = normalize_price(item.get("unitOriginalPrice") or 0) or None

    complement_groups = [
        g for g in (
            parse_complement_group(g, merchant_id)
            for g in (item.get("optionGroups") or item.get("complementGroups") or [])
        )
        if g is not None
    ]

    available = (
        item.get("availability") == "AVAILABLE"
        or item.get("status") == "AVAILABLE"
        or item.get("available", True) is not False
    ) and item.get("enabled", True) is not False

    return {
        "id": item.get("id") or item.get("code"),
        "name": (item.get("description") or item.get("name") or "").strip(),
        "description": (
            item.get("details") or item.get("itemDescription") or item.get("longDescription") or ""
        ).strip()
        or None,
        "price": price,
        "original_price": original_price if original_price != price else None,
        "discount": (
            round((1 - price / original_price) * 100)
            if original_price and original_price > price
            else None
        ),
        "image_url": build_product_image_url(
            item.get("imagePath") or item.get("logoUrl") or item.get("image"),
            merchant_id,
        ),
        "available": available,
        "serves": item.get("serves") or item.get("quantity") or None,
        "complement_groups": complement_groups,
    }


# ─── Categorias ───────────────────────────────────────────────

def parse_category(cat: dict, index: int, merchant_id: str | None = None) -> dict:
    items = [
        parse_item(i, merchant_id)
        for i in (cat.get("itens") or cat.get("items") or [])
        if i.get("description") or i.get("name")
    ]
    return {
        "id": cat.get("id") or cat.get("code") or f"cat-{index}",
        "name": (
            cat.get("friendlyName") or cat.get("name") or cat.get("description") or f"Categoria {index + 1}"
        ).strip(),
        "description": cat.get("details") or None,
        "sort_order": cat.get("sequence") or cat.get("order") or index,
        "items": items,
    }


# ─── Loja ─────────────────────────────────────────────────────

def parse_merchant_graphql(raw: dict) -> dict:
    """
    Extrai nome, logo e capa de data.merchant.resources (merchant-info/graphql).
    """
    merchant = (raw.get("data") or {}).get("merchant") or {}
    logo_file = None
    header_file = None

    for resource in merchant.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        file_name = (resource.get("fileName") or "").strip()
        if not file_name:
            continue
        resource_type = (resource.get("type") or "").upper()
        if resource_type == "LOGO":
            logo_file = file_name
        elif resource_type == "HEADER":
            header_file = file_name

    return {
        "name": (merchant.get("name") or "").strip() or None,
        "logo_url": build_logo_url(logo_file),
        "cover_url": build_header_url(header_file),
    }


def parse_merchant(data: dict) -> dict:
    address = data.get("address") or data.get("deliveryAddress") or {}
    return {
        "name": (data.get("name") or data.get("tradingName") or "").strip() or None,
        "description": (data.get("description") or "").strip() or None,
        "logo_url": None,
        "cover_url": None,
        "address": {
            "street": address.get("streetName", ""),
            "number": address.get("streetNumber", ""),
            "neighborhood": address.get("neighborhood", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "zip_code": address.get("postalCode") or address.get("zipCode", ""),
        } if address.get("streetName") else None,
    }


# ─── Parsers por formato de API ───────────────────────────────

def _merge_store_info(base: dict, overlay: dict) -> dict:
    merged = {**base}
    for key, value in overlay.items():
        if value is not None:
            merged[key] = value
    return merged


def _parse_site_api_catalog(raw: dict, merchant_id: str | None = None) -> list[dict]:
    """site-api: { code: '00', data: { menu: [ { name, itens: [...] } ] } }"""
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    menu = data.get("menu") or raw.get("menu") or []
    categories = [parse_category(cat, i, merchant_id) for i, cat in enumerate(menu)]
    return [c for c in categories if c["items"]]


def _parse_v2_menu(raw: dict, merchant_id: str | None = None) -> list[dict]:
    """marketplace v2: { catalogs: [{ catalog: [...] }] }"""
    all_catalogs = raw.get("catalogs") or raw.get("catalog") or []
    if not all_catalogs:
        return []

    if isinstance(all_catalogs[0], list):
        category_sources = all_catalogs
    else:
        category_sources = [
            c.get("catalog") or c.get("categories") or [] for c in all_catalogs
        ]

    all_cats = [cat for source in category_sources for cat in source if cat]
    categories = [parse_category(cat, i, merchant_id) for i, cat in enumerate(all_cats)]
    return [c for c in categories if c["items"]]


def _parse_v3_catalog(raw: dict, merchant_id: str | None = None) -> list[dict]:
    """marketplace v3: contextSetup.catalogs ou catalogs flat"""
    context = raw.get("contextSetup") or {}
    catalogs = context.get("catalogs") or raw.get("catalogs") or []
    all_cats = []
    for c in catalogs:
        all_cats.extend(c.get("catalog") or c.get("categories") or [])
    if not all_cats:
        all_cats = raw.get("categories") or []

    categories = [parse_category(cat, i, merchant_id) for i, cat in enumerate(all_cats)]
    return [c for c in categories if c["items"]]


def _detect_categories(raw: dict, merchant_id: str | None = None) -> tuple[list[dict], str]:
    """Escolhe o parser conforme o payload (mesma ordem do migrator Node)."""
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    menu = data.get("menu") or raw.get("menu")

    if isinstance(menu, list) and len(menu) > 0:
        return _parse_site_api_catalog(raw, merchant_id), "site_api_catalog"

    if raw.get("contextSetup"):
        cats = _parse_v3_catalog(raw, merchant_id)
        if cats:
            return cats, "catalog_v3"

    if raw.get("catalogs") or raw.get("catalog"):
        cats = _parse_v2_menu(raw, merchant_id)
        if cats:
            return cats, "menu_v2"

    return [], "unknown"


# ─── Entry point ──────────────────────────────────────────────

def parse_catalog_response(
    raw: dict,
    merchant_id: str,
    source_url: str,
    merchant_info: dict | None = None,
) -> dict:
    """
    Parseia a resposta bruta do endpoint /catalog e retorna o schema normalizado.
    merchant_info: resposta opcional de merchant-info/graphql (nome, logo, capa).
    """
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    merchant_data = (
        data.get("merchant")
        or data.get("store")
        or raw.get("merchant")
        or raw.get("store")
        or {}
    )
    store_info = parse_merchant(merchant_data)

    if merchant_info:
        store_info = _merge_store_info(store_info, parse_merchant_graphql(merchant_info))

    categories, data_source = _detect_categories(raw, merchant_id)

    total_items = sum(len(c["items"]) for c in categories)
    items_with_complements = sum(
        1 for c in categories for i in c["items"] if i["complement_groups"]
    )

    return {
        "external_id": merchant_id,
        **store_info,
        "categories": categories,
        "meta": {
            "total_categories": len(categories),
            "total_items": total_items,
            "items_with_complements": items_with_complements,
            "data_source": data_source,
            "scraped_at": __import__("datetime").datetime.now().isoformat(),
            "source_url": source_url,
        },
    }
