# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class LcAccounting(models.Model):
    _name = 'project.config.settings.accounts'
    _rec_name='retention_account'

    retention_account = fields.Many2one('account.account', string='Retention Account',
                                        )
    sub_contract_retention_account = fields.Many2one('account.account', string='Sub-Contracting Retention Account',
                                                     )
    down_payment_account = fields.Many2one('account.account', string='Down Payment Account',
                                           config_parameter='base.down_payment_account')
    sub_contract_down_payment_account = fields.Many2one('account.account',
                                                        string='Sub-Contracting Down Payment Account',
                                                        config_parameter='base.down_payment_account')
    income_account = fields.Many2one('account.account', string='Income Account', config_parameter='base.income_account')
    preliminary_guarantee = fields.Many2one('account.account', string='Preliminary Guarantee Account',
                                            config_parameter='base.preliminary_guarantee')
    bank_commission = fields.Many2one('account.account', string='Bank Commission Account',
                                      config_parameter='base.bank_commission')
    final_guarantee = fields.Many2one('account.account', string='Final Guarantee Account',
                                      config_parameter='base.final_guarantee')
    project_material_cost = fields.Many2one('account.account', string='Project Material Cost Account',
                                            config_parameter='base.project_material_cost')

    @api.constrains('retention_account')
    def _retention_account_con(self):
        if self.retention_account:
            contract = self.env['project.config.settings.accounts'].search(
                [('id', '>', 1), ])
            if contract:
                raise UserError(_('The Accounts Setting Must Be only One '))

