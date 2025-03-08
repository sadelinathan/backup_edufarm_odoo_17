{
    'name': "Expense Approvals",
    'summary': """Expense Approval""",
    'description': """

    """,
    'author': "PT. Japfa Comfeed indonesia",
    'website': "https://vasham.co.id/",
    'category': 'sale',
    'version': '17.0.1.0.0',
    # any module necessary for this one to work correctly
    # this module need dependecies on enterprise module 
    'depends': ['sale', 'approvals', 'web', 'hr_expense'],
    "data": [
        'security/ir.model.access.csv',
        'views/expense_approval.xml',
        'data/email_template.xml',
        'data/report_expense.xml',
        'wizard/expense_refuse_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
