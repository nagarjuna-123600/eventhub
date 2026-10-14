"""Custom exceptions and centralized error handlers."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class BadRequestError(AppError):
    """Business-rule violation, e.g. event is full."""
    status_code = 400
    code = "BAD_REQUEST"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


def _error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return _error_response(err.status_code, err.code, err.message, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return _error_response(err.code, err.name.upper().replace(" ", "_"), err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Unhandled error: %s", err)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")
