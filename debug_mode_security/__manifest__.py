{
    "name": "Debug Mode Security",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "summary": "Control access to Odoo Developer Mode",
    "description": """
Debug Mode Security

This module allows administrators to control which users can
enable or disable Odoo Developer Mode.

Features:
- Restrict access to Developer Mode.
- Restrict access to Assets Debug Mode.
- Restrict access to Test Debug Mode.
- Permission-based access through security groups.
- Compatible with Odoo 18.

Only users assigned to the "Allow Debug Mode" group can
manage debug modes.
    """,
    "author": "Deepak Verma",
    "maintainer": "Deepak Verma",
    "company": "Deecoders",
    "website": "https://www.linkedin.com/in/deepak-verma/",
    "support": "dpakverma789@gmail.com",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "security/restricted_debug_group.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
