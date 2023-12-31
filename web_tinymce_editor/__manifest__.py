{
    'name': 'TinyMCE Widget (Community)',
    'summary': 'Provides a widget for editing HTML fields using tinymce',
    'version': '1.1',
    'description': """Provides a widget for editing HTML fields using tinymce.""",
    'author': 'Gankhuu',
    'category': 'Tools',
    'price': 20.00,
    'currency': 'USD',
    "application": True,
    'depends': ['base', 'base_setup', 'web', 'bus', 'web_editor'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
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
