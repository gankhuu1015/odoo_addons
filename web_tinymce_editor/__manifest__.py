# -*- coding: utf-8 -*-
#################################################################################
# This program is copyright property of the author mentioned above.
# You can't redistribute it and/or modify it.
#################################################################################

{
    'name': 'TinyMCE Widget (Community)',
    'summary': 'Provides a widget for editing HTML fields using TinyMCE',
    'version': '1.1',
    'description': """Provides a widget for editing HTML fields using TinyMCE.""",
    'author': 'Gankhuu',
    'category': 'Tools',
    'price': 15.00,
    'currency': 'USD',
    "application": True,
    'depends': ['base', 'base_setup', 'web', 'web_editor'],
    'data': [
        'security/ir.model.access.csv',
        'views/example_views.xml'
        ],
    'assets': {
        'web.assets_backend': [
            'web_tinymce_editor/static/src/js/web_tinymce.js',
        ],
        'web_editor.assets_wysiwyg': [
            'web_tinymce_editor/static/src/js/wysiwyg.js',
        ],
    },
    'images': ['static/description/windows_main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
