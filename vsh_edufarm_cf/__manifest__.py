# -*- coding: utf-8 -*-
{
    'name': "Edufarm Cash Flow Report",
    'version': '17.0',
    'category': 'Custom',
    'sequence': 1,
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'depends': ['account', 'account_reports', 'account_accountant'],
    'data': [
        'data/account_data.xml',
    ],
}
