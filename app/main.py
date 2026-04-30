import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import Base, engine
from app.exceptions import (
    APIException,
    api_exception_handler,
    generic_exception_handler,
    method_not_allowed_handler,
    not_found_handler,
    validation_exception_handler,
)
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import limiter
from app.routers import admin, auth, profiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Insighta Labs+",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(405, method_not_allowed_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(auth.router)
    app.include_router(profiles.router)
    app.include_router(admin.router)

    return app


app = create_app()
