from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger("eventhub")


class AppError(Exception):
    status_code = 500
    error = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BadRequestError(AppError):
    status_code = 400
    error = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    error = "not_found"


class ConflictError(AppError):
    status_code = 409
    error = "conflict"


def _body(status: int, error: str, message: str, details=None):
    content = {"status": status, "error": error, "message": message}
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return _body(exc.status_code, exc.error, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")),
                "message": e["msg"].removeprefix("Value error, "),
            }
            for e in exc.errors()
        ]
        return _body(400, "validation_error", "Invalid request data.", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        return _body(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(_: Request, exc: IntegrityError):
        logger.warning("Integrity error: %s", exc)
        return _body(409, "conflict", "The request conflicts with existing data.")

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return _body(500, "internal_error", "An unexpected error occurred.")
