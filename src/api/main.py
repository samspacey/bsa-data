"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat, events, health, report, reviews
from src.data.database import get_engine, init_database


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="BSA Voice of Customer API",
        description="API for querying UK building society customer sentiment",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(reviews.router)
    app.include_router(events.router)
    app.include_router(report.router)

    @app.on_event("startup")
    async def _create_tables_if_missing() -> None:
        """Idempotently create any tables the ORM knows about but the DB doesn't.

        Specifically: the analytics_event table is new and isn't in the
        baked-in bsa.db. init_database uses CREATE TABLE IF NOT EXISTS so it's
        safe to run on every boot.
        """
        try:
            init_database(get_engine())
        except Exception as e:  # noqa: BLE001
            print(f"startup init_database warning: {e}")

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "BSA Voice of Customer API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
