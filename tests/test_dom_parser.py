"""Testes unitários do parser DOM."""

from src.scraper.dom_parser import (
    build_catalog_from_dom,
    parse_price_text,
    parse_dom_item,
)
from src.scraper.images import build_product_image_url


MERCHANT_ID = "eb040eab-e24a-4ded-a4b0-421f1629d3b1"


def test_parse_price_text_brazilian():
    assert parse_price_text("R$ 24,99") == 2499
    assert parse_price_text("R$ 1.234,56") == 123456
    assert parse_price_text("a partir de 12,90") == 1290
    assert parse_price_text("+ R$ 2,50") == 250
    assert parse_price_text("") == 0


def test_parse_dom_item_garnish_complements():
    item = parse_dom_item(
        {
            "id": "prato-1",
            "name": "X-Salada",
            "priceText": "R$ 20,00",
            "complementGroups": [
                {
                    "name": "Escolha os adicionais:",
                    "options": [
                        {
                            "id": "grp-opt-ovo",
                            "name": "Ovo",
                            "priceText": "+ R$ 2,50",
                        }
                    ],
                }
            ],
        },
        MERCHANT_ID,
    )
    assert len(item["complement_groups"]) == 1
    assert item["complement_groups"][0]["options"][0]["name"] == "Ovo"
    assert item["complement_groups"][0]["options"][0]["price"] == 250
    assert item["complement_groups"][0]["options"][0]["id"] == "grp-opt-ovo"


def test_build_product_image_url_with_pratos_prefix():
    path = f"{MERCHANT_ID}/202110221859_YRUL_i.jpg"
    url = build_product_image_url(path, MERCHANT_ID)
    assert url == (
        f"https://static-images.ifood.com.br/image/upload/t_high/pratos/{path}"
    )


def test_parse_dom_item_shape():
    prato = "a4700583-e4a4-4e5b-9fdb-a6648194df46"
    item = parse_dom_item(
        {
            "name": "Batatinha",
            "priceText": "R$ 9,50",
            "detailsText": "Porcao individual",
            "href": f"?prato={prato}",
            "imageSrc": (
                f"https://static.ifood-static.com.br/image/upload/t_low/pratos/"
                f"{MERCHANT_ID}/202403221833_W8P2_i.jpg"
            ),
            "complementGroups": [],
        },
        MERCHANT_ID,
    )
    assert item["name"] == "Batatinha"
    assert item["id"] == prato
    assert item["price"] == 950
    assert item["description"] == "Porcao individual"
    assert "/t_high/" in (item["image_url"] or "")
    assert "complement_groups" in item


def test_build_catalog_from_dom_schema():
    dom_data = {
        "store": {
            "name": "Magrelo Lanches",
            "logoSrc": f"https://static.ifood-static.com.br/image/upload/t_thumbnail/logosgde/{MERCHANT_ID}/logo.jpg",
            "coverSrc": None,
        },
        "categories": [
            {
                "id": "menu-group-LCH",
                "name": "Combos",
                "items": [
                    {
                        "id": "1",
                        "name": "Burger",
                        "priceText": "R$ 10,00",
                        "imageSrc": f"https://static-images.ifood.com.br/image/upload/t_high/pratos/{MERCHANT_ID}/x.jpg",
                        "customizable": False,
                    }
                ],
            }
        ],
        "totalCards": 1,
    }
    result = build_catalog_from_dom(dom_data, MERCHANT_ID, "https://www.ifood.com.br/delivery/test")
    assert result["external_id"] == MERCHANT_ID
    assert result["name"] == "Magrelo Lanches"
    assert result["meta"]["data_source"] == "dom_ui"
    assert result["meta"]["total_items"] == 1
    assert len(result["categories"]) == 1
    assert result["categories"][0]["id"] == "menu-group-LCH"
    assert result["categories"][0]["name"] == "Combos"
    assert "pratos" in (result["categories"][0]["items"][0]["image_url"] or "")
