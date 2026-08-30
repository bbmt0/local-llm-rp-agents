from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
load_dotenv()
import logging
from app.core.logging import setup_logging
from app.api.routes.agents import router as agents_router
from app.api.routes.health import router as health_router

setup_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Boosted NPC API",
        version="0.1.0",
    )

    app.include_router(health_router)
    app.include_router(agents_router)

    return app


app = create_app()
logger.info(app.title + " running")