# -*- coding: utf-8 -*-
{
    'name': "construction_system",

    'summary': """
       Construction System""",

    'description': """
         Construction System
    """,

    'author': "Mohamed Abdelbaset",
    'category': 'Construction',
    'version': '14.0.1',
    'depends': ['base','project','stock','sale','hr','mail',],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/bid_requirement_wizard.xml',
        'views/project.xml',
        'views/project_quotation.xml',
        'views/preliminary_gurantee_recovery.xml',
        'views/project_works_category.xml',
        'views/task.xml',
        'views/setting.xml',
        # 'views/project_invoice.xml',
        'views/preliminary_gurantee.xml',
        'views/stock.xml',
        'views/project_planning.xml',
        'views/asset_in.xml',
        'views/asset_out.xml',
        'views/project_custody.xml',
        'views/clearance_custody.xml',
        'views/down_payment_invoices.xml',
        'views/progress_bill_invoices.xml',
        'views/gurantee.xml',
        'views/project_contract.xml',
        'views/sub_contract_agrement.xml',
        'views/subcontract_rfq.xml',
        'views/retention_claim.xml',
        'views/final_gurantee_recovery.xml',
        'views/project_costing_board.xml',
        # 'reports/quotation.xml',
        # 'reports/subcontract_rfq.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}