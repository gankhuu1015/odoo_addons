{
    'name': 'Tavan bogd payroll',
    'version': '1.0',
    'author': 'individual',
    'category': 'Tools',
    'description': """payroll custom""",
    'summary': 'tb hr insured type',
    'license': 'LGPL-3',
    'version': '1.0',
    'sequence': 1,
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/insured_type_views.xml',
    ],
    'images': ['static/description/tavanbogd.png'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}