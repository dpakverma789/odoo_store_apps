{
    "name": "Single Session Login Pro",
    "summary": "Session policies, idle logout, administrator control and session history",
    "version": "19.0.1.0.1",
    "category": "Administration",
    "author": "Deepak Verma",
    "maintainer": "Deepak Verma",
    "company": "Deecoders",
    "website": "https://www.linkedin.com/in/deepak-verma-07144012a",
    "support": "dpakverma789@gmail.com",
    "description": """
Extends Single Session Login with replace-or-reject login policies, server-enforced
idle logout and warnings, administrator session termination, basic session history,
and configurable history retention. Requires the Free addon in the addons path.
""",
    "license": "OPL-1",
    "price": 29.00,
    "currency": "EUR",
    "depends": ["single_session_login", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/user_session_views.xml",
        "views/res_config_settings_views.xml",
        "views/login_templates.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("replace", "single_session_login/static/src/js/session_checker.js",
             "single_session_login_pro/static/src/js/session_checker.js"),
        ],
    },
    "application": True,
    "auto_install": False,
    "installable": True,
}
