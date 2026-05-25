import pytest

from src.config import config
from src.db.database import close_db, init_db


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_scraper.db"
    monkeypatch.setattr(config, "DATABASE_PATH", str(db_path))
    await init_db()
    yield db_path
    await close_db()


@pytest.fixture
def sample_ifood_url():
    return (
        "https://www.ifood.com.br/delivery/londrina-pr/loja-teste/"
        "eb040eab-e24a-4ded-a4b0-421f1629d3b1"
    )
