import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.config import PROJECT_ROOT, Settings
from app.main import create_app, get_ollama_client


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Isolate tests from developer environment variables and the real .env.
    for key in ("OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS", "DATABASE_PATH"):
        monkeypatch.delenv(key, raising=False)
    return create_app(Settings(_env_file=None, database_path=tmp_path / "test.db"))


def mock_ollama(app, handler):
    async def override():
        async with httpx.AsyncClient(
            base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
        ) as client:
            yield client

    app.dependency_overrides[get_ollama_client] = override


def test_backend_health_creates_local_database(app):
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok", "service": "OpsPilot API", "database": "connected"
        }
        assert app.state.engine.url.database.endswith("test.db")


def test_database_failure_is_unhealthy(app, monkeypatch):
    def broken_database(engine):
        raise OperationalError("SELECT 1", {}, Exception("unavailable"))

    monkeypatch.setattr("app.main.check_database", broken_database)
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_ollama_model_available(app):
    def handler(request):
        assert request.url == "http://localhost:11434/api/tags"
        assert request.method == "GET"
        return httpx.Response(200, json={"models": [{"name": "qwen3.5:9b"}]})

    mock_ollama(app, handler)
    with TestClient(app) as client:
        response = client.get("/api/health/ollama")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model"] == "qwen3.5:9b"


def test_ollama_model_missing(app):
    mock_ollama(app, lambda request: httpx.Response(200, json={"models": []}))
    with TestClient(app) as client:
        response = client.get("/api/health/ollama")
    assert response.status_code == 503
    assert response.json()["status"] == "model_missing"


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
def test_ollama_connection_failure_does_not_break_backend(app, error):
    def handler(request):
        raise error("Ollama offline", request=request)

    mock_ollama(app, handler)
    with TestClient(app) as client:
        response = client.get("/api/health/ollama")
        assert client.get("/api/health").status_code == 200
    assert response.status_code == 503
    assert response.json()["status"] == "unreachable"


@pytest.mark.parametrize("body", [{}, {"models": None}, {"models": [{}]}, "not-json"])
def test_malformed_ollama_response(app, body):
    mock_ollama(app, lambda request: httpx.Response(200, text=body) if isinstance(body, str)
                else httpx.Response(200, json=body))
    with TestClient(app) as client:
        response = client.get("/api/health/ollama")
    assert response.status_code == 503
    assert response.json()["status"] == "invalid_response"


@pytest.mark.parametrize("status_code", [302, 500])
def test_ollama_http_errors_and_redirects(app, status_code):
    mock_ollama(app, lambda request: httpx.Response(status_code, headers={"Location": "https://example.com"}))
    with TestClient(app) as client:
        response = client.get("/api/health/ollama")
    assert response.status_code == 503


@pytest.mark.parametrize("url", ["https://example.com", "http://192.168.1.1:11434", "http://localhost:11434/api", "http://user@localhost:11434"])
def test_remote_or_invalid_ollama_urls_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ollama_base_url=url)


def test_database_path_stays_in_repository():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_path=PROJECT_ROOT.parent / "outside.db")
