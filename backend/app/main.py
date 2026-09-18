"""Application entrypoint: middleware, error handling, router wiring."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.database import Base, engine
from app.routers import auth, quotations, rfqs

logger = logging.getLogger("rfq")
settings = get_settings()

app = FastAPI(
    title="Mini B2B RFQ Marketplace",
    version="1.0.0",
    description="Buyers post requirements; suppliers discover them and quote.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Refuse to boot in production with the built-in dev secret. Anyone who
    # knows it could mint a token for any account, so failing loudly here is
    # far better than running an app whose auth is decorative.
    if settings.is_production and settings.jwt_secret == Settings.model_fields["jwt_secret"].default:
        raise RuntimeError("JWT_SECRET must be set to a unique value in production")

    # Schema is created from the models at boot. For an assignment of this size
    # that is enough; a long-lived product would use Alembic migrations so
    # schema changes are versioned and reversible. See README > Limitations.
    Base.metadata.create_all(bind=engine)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn Pydantic's nested error list into one readable sentence.

    The frontend shows `detail` verbatim, so it has to be human-readable.
    """
    messages = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query"))
        messages.append(f"{field}: {err['msg']}" if field else err["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(messages) or "Invalid request"},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the real traceback, return a generic message.

    Stack traces and driver errors must never reach the client - they leak
    table names, file paths and library versions.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong. Please try again."},
    )


app.include_router(auth.router)
app.include_router(rfqs.router)
app.include_router(quotations.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
