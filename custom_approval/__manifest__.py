{
    'name': "Approvals",
    'summary': """Custom Approval""",
    'description': """

    """,
    'author': "PT. Japfa Comfeed indonesia",
    'website': "https://vasham.co.id/",
    'category': 'sale',
    'version': '17.0.1.0.0',
    # any module necessary for this one to work correctly
    # this module need dependecies on enterprise module 
    'depends': ['sale', 'approvals', 'web', 'contacts'],
    "data": [
        # 'security/approval_group.xml',
        'security/ir.model.access.csv',
        'views/view_approval.xml',
        'views/user_approval.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
