"""Application entry point: builds the FastAPI app and wires everything together.

Run with:  uvicorn app.main:app --reload
"""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import addresses
from app.core.config import get_settings
from app.core.exceptions import AddressNotFoundError
from app.core.logging import configure_logging
from app.db.session import engine, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare resources on startup and release them on shutdown."""
    init_db()
    logger.info("Application started (version %s)", __version__)
    yield
    engine.dispose()
    logger.info("Application stopped")


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log method, path, status code and duration of every request."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


async def address_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Translate the domain error into an HTTP 404."""
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Create, read, update and delete addresses with coordinates, and find "
            "addresses within a given distance of a point."
        ),
        lifespan=lifespan,
    )
    app.middleware("http")(log_requests)
    app.add_exception_handler(AddressNotFoundError, address_not_found_handler)
    app.include_router(addresses.router)

    @app.get("/health", tags=["health"], summary="Liveness check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
