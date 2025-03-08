# -*- coding: utf-8 -*-

{
    'name': 'Odoo 16 EDUFARM Create Edit Off',
    'version': '16.0.1.0.0',
    'category': 'Odoo 16 EDUFARM Create Edit Off',
    'summary': 'Odoo 16 EDUFARM Create Edit Off',
    'description': 'Odoo 16 EDUFARM Create Edit Off',
    'sequence': '1',
    'author': 'Novran Ardianto',
    'support': 'novran.ardianto@gmail.com',
    'depends': ['purchase', 'stock', 'account'],
    "data": [
        'views/purchase_order_form.xml',
        'views/stock_warehouse_orderpoint.xml',
        'views/stock_picking.xml',
        'views/stock_scrap.xml',
        'views/account_move.xml',
        'views/account_payment.xml'
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
