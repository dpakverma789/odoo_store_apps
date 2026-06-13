{
    "name": "Hide Server Error Details",
    "summary": "Hide technical tracebacks and display user-friendly error messages",
    "description": """
Hide Server Error Details improves security and user experience by preventing
technical tracebacks, debug information, file paths and internal system details
from being displayed to end users.

Key Features:

* Hide technical traceback details
* Protect sensitive system information
* Display professional error messages
* Improve user experience
* Lightweight and upgrade-safe
* Odoo 18 compatible
  """,
    "author": "Deepak Verma",
    "maintainer": "Deepak Verma",
    "company": "Deecoders",
    "website": "https://www.linkedin.com/in/deepak-verma-07144012a",
    "support": "[dpakverma789@gmail.com](mailto:dpakverma789@gmail.com)",
    "license": "LGPL-3",
    "category": "Administration",
    "version": "18.0.1.0.0",

    "depends": [
        "web",
    ],

    "assets": {
        "web.assets_backend": [
            "hide_server_traceback/static/src/js/error_dialog_patch.js",
            "hide_server_traceback/static/src/css/error_dialog_patch.css",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}
