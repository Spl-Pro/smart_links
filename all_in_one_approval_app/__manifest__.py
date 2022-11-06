
# -*- coding: utf-8 -*-

{
    'name' : 'All in One Approval Management App',
    'author': "Edge Technologies",
    'version' : '15.0.1.1',
    'live_test_url':'https://youtu.be/T6DFldwvp3o',
    "images":['static/description/main_screenshot.png'],
    'summary' : 'All in One Approval Workflow All in One Dynamic Approval All Sale Order Approval Purchase Approval Invoice Approval Dashboard Dynamic Approval All in One Dynamic Approval Request for Approval All in One Request Approval Request Approval Workflow Request',
    'description' : """
        Approval Management Odoo App
    """,
    'depends' : ['base','hr','sale_management','purchase'],
    "license" : "OPL-1",
    'data' : [
            'security/approval_security.xml',
            'security/ir.model.access.csv',
            'data/approve_tempale.xml',
            'wizard/approve_request.xml',
            'wizard/approve_request_sale.xml',
            'views/approval_type.xml',
            'views/approvals.xml',
            'views/purchase.xml',
            'views/sale.xml',
            ],
    'qweb' : [],
    'demo' : [],
    'installable' : True,
    'auto_install' : False,
    'price': 49,
    'currency': "EUR",
    'category' : 'Sales',
}
