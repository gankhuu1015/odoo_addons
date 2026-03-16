{
    "name": "POS QPay",
    "version": "19.0.1.0.0",
    "author": "Gankhuu",
    "category": "Sales/Point of Sale",
    "summary": "QPay payment terminal flow for POS",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/qpay_payment_method_data.xml",
        "views/pos_payment_method_views.xml",
        "views/qpay_transaction_views.xml"
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "sb_qpay_pos/static/src/js/**/*.js",
            "sb_qpay_pos/static/src/xml/**/*.xml"
        ]
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    'currency': 'USD',
    'price': 40.00,
}
