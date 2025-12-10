from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.agents import router as agents_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Boosted NPC API",
        version="0.1.0",
    )

    @app.get("/health")
    async def healthcheck() -> JSONResponse:
        return JSONResponse(content={"status": "ok"})

    app.include_router(agents_router)

    return app


app = create_app()
