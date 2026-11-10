import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel

from app.config import PROJECT_ROOT, Settings
from app.database import check_database, create_database_engine
from app.orders import router as orders_router, seed_orders
from app.drafts import router as drafts_router
from app.workflow import router as workflow_router
from app.migrations import migrate_database
from app.tickets import get_ollama_client, router as tickets_router


class BackendHealth(BaseModel):
    status: Literal["ok", "error"]
    service: str = "OpsPilot API"
    database: Literal["connected", "unavailable"]
    isolated_qa: bool = False


class OllamaHealth(BaseModel):
    status: Literal["ok", "unreachable", "model_missing", "invalid_response"]
    model: str
    message: str


class InstalledModel(BaseModel):
    name: str


class OllamaTags(BaseModel):
    models: list[InstalledModel]


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(config.database_path)
        app.state.engine = engine
        try:
            migrate_database(engine, config.database_path)
            seed_orders(engine)
            app.state.settings = config
            app.state.classification_lock = asyncio.Lock()
            # Ignore proxy settings and redirects so all Ollama requests stay local.
            async with httpx.AsyncClient(
                base_url=config.ollama_base_url,
                timeout=config.ollama_timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                app.state.ollama_client = client
                yield
        finally:
            engine.dispose()

    app = FastAPI(title="OpsPilot API", version="0.4.0", lifespan=lifespan)
    app.include_router(tickets_router)
    app.include_router(orders_router)
    app.include_router(drafts_router)
    app.include_router(workflow_router)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=503, content={"detail": {
            "code": "database_unavailable",
            "message": "Local ticket storage is unavailable. Check the backend and refresh the ticket list before retrying.",
        }})

    @app.get("/api/health", response_model=BackendHealth)
    def health(request: Request, response: Response):
        try:
            check_database(request.app.state.engine)
        except SQLAlchemyError:
            response.status_code = 503
            return BackendHealth(status="error", database="unavailable")
        return BackendHealth(status="ok", database="connected",
                             isolated_qa=config.database_path == PROJECT_ROOT / "data" / "milestone3b-qa.db")

    @app.get("/api/health/ollama", response_model=OllamaHealth)
    async def ollama_health(
        response: Response,
        client: Annotated[httpx.AsyncClient, Depends(get_ollama_client)],
    ):
        try:
            result = await client.get("/api/tags")
            result.raise_for_status()
        except httpx.HTTPError:
            response.status_code = 503
            return OllamaHealth(
                status="unreachable", model=config.ollama_model,
                message="Cannot reach local Ollama. Check that it is running.",
            )
        try:
            tags = OllamaTags.model_validate(result.json())
        except ValueError:
            response.status_code = 503
            return OllamaHealth(
                status="invalid_response", model=config.ollama_model,
                message="Local Ollama returned an unexpected model list.",
            )
        if config.ollama_model not in {model.name for model in tags.models}:
            response.status_code = 503
            return OllamaHealth(
                status="model_missing", model=config.ollama_model,
                message=f"Ollama is running, but {config.ollama_model} is not installed.",
            )
        return OllamaHealth(
            status="ok", model=config.ollama_model,
            message="Ollama is reachable and the configured model is installed.",
        )

    return app


app = create_app()
