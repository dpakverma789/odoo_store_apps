{
    "name": "Single Session Login Pro",
    "summary": "Session policies, idle logout, administrator control and session history",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "author": "Deepak Verma",
    "license": "OPL-1",
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
    "installable": True,
}
