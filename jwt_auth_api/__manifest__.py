# -*- coding: utf-8 -*-
{
    "name": "JWT Auth API for Odoo",
    "summary": "JWT-based authentication endpoints for Odoo (Access/Refresh token, Revoke)",
    "description": """
JWT Auth API for Odoo

Features:
- Generate/refresh access token using refresh token
- Rotate refresh token
- Revoke refresh token (logout)
- Browser support via HttpOnly cookie for refresh token

Technical:
- Implemented using Odoo HTTP JSON controllers
- Includes security groups and access rights
""",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "author": "Gankhuu",
    "license": "AGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/connection_api_views.xml",
    ],
    'price': 50.00,
    'currency': 'USD',
    "post_init_hook": "_install_jwt",
    'images': [
        'static/description/icon.png',
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}