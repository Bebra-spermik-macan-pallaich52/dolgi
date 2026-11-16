import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1.client_api_router import router as client_router
from app.api.v1.tarif_api_router import router as tarif_router
from app.core.exceptions import ConflictError, NotFoundError
from app.db.database import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        yield
    finally:
        close_db()


main_app = FastAPI(
    title="dolg8", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)
app_v1 = FastAPI(title="Телефонные номера", version="1.0.0", lifespan=lifespan)
app_v1.include_router(client_router)
app_v1.include_router(tarif_router)
main_app.mount("/api/v1", app_v1)


@app_v1.exception_handler(RequestValidationError)
@app_v1.exception_handler(ValidationError)
async def validation_error(request: Request, exc):
    errors = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app_v1.exception_handler(NotFoundError)
async def not_found(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app_v1.exception_handler(ConflictError)
async def conflict(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app_v1.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Нарушение целостности данных."})


@app_v1.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.error("Ошибка запроса к базе данных")
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера."})


@main_app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/api/v1/docs")
