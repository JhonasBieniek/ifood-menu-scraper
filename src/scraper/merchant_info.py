"""
Captura e validação da API merchant-info/graphql (nome, logo, header).
"""

MERCHANT_GRAPHQL_PATH = "/site-api/v1/merchant-info/graphql"


def build_merchant_graphql_url(
    latitude: str = "",
    longitude: str = "",
    channel: str = "IFOOD",
) -> str:
    return (
        f"https://www.ifood.com.br{MERCHANT_GRAPHQL_PATH}"
        f"?latitude={latitude}&longitude={longitude}&channel={channel}"
    )


def is_valid_merchant_info(body: dict | None) -> bool:
    if not body or not isinstance(body, dict):
        return False
    merchant = (body.get("data") or {}).get("merchant")
    if not merchant or not isinstance(merchant, dict):
        return False
    name = (merchant.get("name") or "").strip()
    return bool(name)
