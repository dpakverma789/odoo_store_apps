{
    "name": "Disable Login Autocomplete",
    "summary": "Disable browser autocomplete on the Odoo login page to enhance security.",
    "description": """
Disable Login Autocomplete
==========================

This module disables browser autocomplete and autofill on the Odoo login form.

Why use this module?
--------------------
Browsers often store usernames and passwords automatically. In shared or public
systems this may expose sensitive credentials.

Features
--------
- Disable autocomplete for username and password fields
- Prevent browser autofill on the login form
- Lightweight and secure implementation
- No impact on existing authentication logic
- Compatible with standard Odoo login page

Technical Details
-----------------
The module overrides the default login template and adds attributes such as:
- autocomplete="off"
- autocomplete="new-password"

These attributes prevent browsers from storing or suggesting credentials.

Author
------
Deepak Verma
Company: Deecoders
Email: dpakverma789@gmail.com
""",

    "version": "18.0.1.0.0",
    "category": "Security",
    "license": "LGPL-3",
    "author": "Deepak Verma",
    "maintainer": "Deepak Verma",
    "website": "https://www.linkedin.com/in/deepak-verma-07144012a",

    "depends": ["web"],

    "data": [
        "views/login_template.xml",
    ],

    "images": [
        "static/description/banner.png",
        "static/description/screenshot1.png",
        "static/description/screenshot2.png",
    ],

    'assets': {
        'web.assets_frontend': [
            'disable_login_autocomplete/static/src/js/login_security.js',
        ],
    },

    "application": False,
    "installable": True,
    "auto_install": False,
    "support": "dpakverma789@gmail.com",

}
