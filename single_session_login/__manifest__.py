{
    "name": "Single Session Login",
    "summary": "Control concurrent user logins with flexible single-session management.",
    "description": """
Single Session Login allows administrators to restrict users to a single active session
while providing the flexibility to allow multiple sessions for selected users.
Improve security, prevent account sharing, and manage user access across devices.
""",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "license": "LGPL-3",

    "author": "Deepak Verma",
    "maintainer": "Deepak Verma",
    "company": "Deecoders",

    "website": "https://www.linkedin.com/in/deepak-verma-07144012a",

    "support": "dpakverma789@gmail.com",

    "depends": [
        "base",
        "web",
    ],

    "data": [
        "views/res_users_views.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "single_session_login/static/src/js/session_checker.js",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,

}
