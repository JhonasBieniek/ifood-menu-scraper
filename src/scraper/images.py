"""
URLs de imagens do iFood (CDNs e prefixos por tipo de asset).
"""

PRODUCT_CDN = "https://static-images.ifood.com.br/image/upload"
STORE_CDN = "https://static.ifood-static.com.br/image/upload"


def _normalize_path(path: str) -> str:
    return path.lstrip("/").replace("\\", "/")


def build_product_image_url(
    path: str | None,
    merchant_id: str | None = None,
    quality: str = "t_high",
) -> str | None:
    """
    Produtos: static-images + t_high/pratos/{merchant_id}/{arquivo}.jpg
    """
    if not path:
        return None
    path = _normalize_path(path)
    if path.startswith("http"):
        return path

    if merchant_id and not path.startswith(f"{merchant_id}/") and not path.startswith("pratos/"):
        path = f"{merchant_id}/{path}"
    if not path.startswith("pratos/"):
        path = f"pratos/{path}"

    return f"{PRODUCT_CDN}/{quality}/{path}"


def build_logo_url(file_name: str | None) -> str | None:
    """
    Logo: static.ifood-static + t_thumbnail/logosgde/{fileName}
    fileName já vem como {merchantId}/{arquivo}.jpg
    """
    if not file_name or not str(file_name).strip():
        return None
    path = _normalize_path(str(file_name))
    if path.startswith("http"):
        return path
    return f"{STORE_CDN}/t_thumbnail/logosgde/{path}"


def build_header_url(file_name: str | None) -> str | None:
    """
    Capa/header: static.ifood-static + capa/{fileName}
    """
    if not file_name or not str(file_name).strip():
        return None
    path = _normalize_path(str(file_name))
    if path.startswith("http"):
        return path
    return f"{STORE_CDN}/capa/{path}"
