import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    for key in ("OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS", "CLASSIFICATION_TIMEOUT_SECONDS", "DATABASE_PATH"):
        monkeypatch.delenv(key, raising=False)
    return create_app(Settings(_env_file=None, database_path=tmp_path / "test.db"))
