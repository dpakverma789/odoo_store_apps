import logging
from odoo.http import JsonRPCDispatcher

_logger = logging.getLogger(__name__)

_original_handle_error = JsonRPCDispatcher.handle_error


def custom_handle_error(self, exc):
    """
    Global JSON-RPC Exception Handler

    Covers:
    - Odoo Web Client
    - Browser Network Responses
    - Postman JSON-RPC APIs
    - Custom Odoo APIs (type='json')

    Hides:
    - traceback
    - debug
    - file paths
    - model names
    - addon names
    """

    _logger.exception("Unhandled Exception", exc_info=exc)
    _logger.error("CUSTOM HANDLE ERROR CALLED")
    error = {
        "code": 500,
        "message": "Internal Server Error",
        "data": {
            "name": "InternalServerError",
            "message": "Something went wrong. Please contact administrator.",
            "arguments": [],
            "context": {},
        },
    }

    return self._response(error=error)


JsonRPCDispatcher.handle_error = custom_handle_error