# -*- coding: utf-8 -*-
{
    'name': "Edufarm Cash Flow Report",
    'version': '16',
    'category': 'Custom',
    'sequence': 1,
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3', 
    'depends': ['account','account_reports'],
    'data': [
        'data/account_data.xml',
    ],
}
