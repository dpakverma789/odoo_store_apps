import logging

from odoo.http import (
    JsonRPCDispatcher,
    serialize_exception,
    NotFound,
    SessionExpiredException,
)
from odoo.exceptions import (
    ValidationError,
    UserError,
    AccessError,
    AccessDenied,
    MissingError,
    RedirectWarning
)

_logger = logging.getLogger(__name__)

_original_handle_error = JsonRPCDispatcher.handle_error


BUSINESS_EXCEPTIONS = (
    ValidationError,
    UserError,
    AccessError,
    AccessDenied,
    MissingError,
    RedirectWarning
)


def custom_handle_error(self, exc):
    """
    Global JSON-RPC Exception Handler

    Business Exceptions
    -------------------
    Preserve Odoo behaviour.

    Unexpected Exceptions
    ---------------------
    Hide traceback/debug information from API response
    while logging complete traceback on the server.
    """

    # Preserve original Odoo behaviour
    if isinstance(exc, BUSINESS_EXCEPTIONS):
        return _original_handle_error(self, exc)

    # Log full traceback on server
    _logger.exception("Unhandled Exception", exc_info=exc)

    # Build default Odoo error response
    error = {
        "code": 200,
        "message": "Odoo Server Error",
        "data": serialize_exception(exc),
    }

    # Preserve Odoo special cases
    if isinstance(exc, NotFound):
        error["code"] = 404
        error["message"] = "404: Not Found"

    elif isinstance(exc, SessionExpiredException):
        error["code"] = 100
        error["message"] = "Odoo Session Expired"

    data = error.get("data") or {}

    # -------------------------------------------------
    # Remove sensitive information from client response
    # -------------------------------------------------

    data["debug"] = ""
    data["arguments"] = []
    data["context"] = {}

    # Generic message shown to user
    data["message"] = "Something went wrong. Please contact your administrator."

    # Replace real exception class
    data["name"] = "InternalServerError"

    # Remove extra technical fields if available
    data.pop("exceptionName", None)
    data.pop("exception_type", None)

    # Custom frontend flag
    data["hide_server_error"] = True

    error["data"] = data

    return self._response(error=error)


JsonRPCDispatcher.handle_error = custom_handle_error