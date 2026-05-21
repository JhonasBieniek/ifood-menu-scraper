import re
from urllib.parse import urlparse

# iFood URLs modernas incluem o UUID completo no path:
# https://www.ifood.com.br/delivery/londrina-pr/magrelo-lanches-.../eb040eab-e24a-4ded-a4b0-421f1629d3b1
UUID_PATTERN = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    re.IGNORECASE,
)

IFOOD_URL_PATTERN = re.compile(
    r"^https?://(www\.)?ifood\.com\.br/delivery/",
    re.IGNORECASE,
)


def validate_ifood_url(url: str) -> bool:
    return bool(IFOOD_URL_PATTERN.match(url))


def extract_merchant_id(url: str) -> str | None:
    """
    Tenta extrair o UUID do merchant diretamente da URL.
    Funciona com o formato moderno do iFood que inclui o UUID no path.
    """
    match = UUID_PATTERN.search(url)
    return match.group(0).lower() if match else None


def extract_merchant_id_or_raise(url: str) -> str:
    if not validate_ifood_url(url):
        raise ValueError(
            "URL inválida. Use o formato: "
            "https://www.ifood.com.br/delivery/{cidade}/{loja}/{uuid}"
        )

    merchant_id = extract_merchant_id(url)
    if not merchant_id:
        raise ValueError(
            "UUID do merchant não encontrado na URL. "
            "Certifique-se de usar a URL completa da loja no iFood, "
            "incluindo o identificador ao final."
        )

    return merchant_id
