# -*- coding: utf-8 -*-
{
    'name': "SPl_DRC_invoice_report",

    'summary': """
        Invoice report""",

    'description': """
        Invoice report
    """,

    'author': "AFAQ AL SPL TRADING EST",
    'website': "WWW.SPL-PRO.COM",
    'category': 'Accounting',
    'version': '15.0.1',

    'depends': ['base','account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'reports/e_invoice_standard.xml',
        'reports/e_credit_note.xml',
        # 'reports/invoice.xml',
    ],

}