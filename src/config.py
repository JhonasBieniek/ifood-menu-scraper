import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PORT: int = int(os.getenv("PORT", "3001"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    API_KEY: str | None = os.getenv("API_KEY")

    # dom      → Pure UI (Camoufox + DOM visível)
    # network  → só interceptação de rede (site-api)
    # auto     → dom primeiro, fallback network (padrão)
    SCRAPER_STRATEGY: str = os.getenv("SCRAPER_STRATEGY", "auto")

    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))
    SCRAPE_TIMEOUT_S: int = int(os.getenv("SCRAPE_TIMEOUT_S", "60"))
    MAX_ITEMS_DETAIL: int = int(os.getenv("MAX_ITEMS_DETAIL", "40"))
    SCRAPER_DEBUG: bool = os.getenv("SCRAPER_DEBUG", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")


config = Config()
