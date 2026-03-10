{
    "name": "Odoo Field Syntax Generator",
    "version": "18.0.1.0.0",
    "summary": "Generate Odoo Python and XML field syntax automatically",

    "description": """
Odoo Field Syntax Generator
===========================

A lightweight developer utility that helps generate Odoo Python field 
definitions and XML view field tags from a simple variable notation.

Key Features
------------
- Generate Python field syntax automatically
- Generate XML view field tags
- Supports common Odoo field types
- Improves developer productivity
- Reduces repetitive coding
""",

    "author": "Deepak Verma",
    "company": "Deecoders",
    "website": "https://www.linkedin.com/in/deepak-verma-07144012a",
    "maintainer": "Deepak Verma",
    "email": "dpakverma789@gmail.com",

    "category": "Developer Tools",
    "license": "LGPL-3",

    "depends": ["base"],

    "data": [
        "security/ir.model.access.csv",
        "views/generator_view.xml",
    ],

    "images": [
        "static/description/banner.png"
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}
