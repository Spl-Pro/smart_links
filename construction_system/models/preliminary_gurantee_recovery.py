# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class PreliminaryGuranteeRecovery(models.Model):
    _name = 'preliminary.gurantee.recovery'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Transaction Number", readonly=True)
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                              default='draft')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer')
    bank_account_id = fields.Many2one('account.account', string='Bank Account', related='project_id.bank_commission')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_id2 = fields.Many2one('account.move', string='Clear Gurantee Recovery Entry')
    date = fields.Date('Date', default=datetime.today())
    preliminary_gurantee_amount = fields.Float('Preliminary Gurantee Amount')
    bank_commission = fields.Float('Bank Commission')
    note = fields.Text('Description')
    is_clear_gurantee = fields.Boolean('is_clear_gurantee')
    awarded = fields.Boolean(related='project_id.awarded')
    preliminary_gurantee_id = fields.Many2one(comodel_name="preliminary.gurantee", string="Preliminary Gurantee",
                                              )

    @api.onchange('project_id')
    def compute_preliminary_gurantee(self):
        for rec in self:
            preliminary = self.env['preliminary.gurantee'].search([('project_id', '=', self.project_id.id)])
            rec.preliminary_gurantee_id = preliminary.id
            res = {}
            if self.project_id:
                res['domain'] = {'preliminary_gurantee_id': [('project_id', '=', self.project_id.id)]}
            else:
                res['domain'] = {'preliminary_gurantee_id': []}
            return res

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('preliminary.gurantee.recovery')
        vals['number'] = sequence or '/'
        return super(PreliminaryGuranteeRecovery, self).create(vals)

    def clear_gurantee(self):
        for rec in self:
            for rec in self:
                move2 = self.env['account.move'].create({
                    'journal_id': rec.journal_id.id,
                    'date': rec.date,
                    'project_id': rec.project_id.id,
                    'ref': rec.number + '-' + rec.project_id.name,
                })
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {
                        'move_id': move2.id,
                        'account_id': rec.bank_account_id.id,
                        'name': rec.project_id.name,
                        'partner_id': rec.partner_id.id,
                        'analytic_account_id': rec.project_id.analytic_account_id.id,
                        'debit': rec.preliminary_gurantee_amount,
                        'credit': 0.0,
                    })
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {
                        'move_id': move2.id,
                        'account_id': rec.project_id.preliminary_guarantee.id,
                        'analytic_account_id': rec.project_id.analytic_account_id.id,
                        'name': rec.project_id.name,
                        'partner_id': rec.partner_id.id,
                        'debit': 0.0,
                        'credit': rec.preliminary_gurantee_amount,

                    })
                rec.move_id2 = move2.id
                rec.is_clear_gurantee = True

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            preliminary = self.env['preliminary.gurantee.recovery'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if preliminary:
                raise UserError(_('You Have Preliminary Gurantee Recovery For This Project'))

    def confirm_quotation(self):
        for rec in self:
            move = self.env['account.move'].create({
                'journal_id': rec.journal_id.id,
                'date': rec.date,
                'project_id': rec.project_id.id,
                    'ref': rec.number + '-' + rec.project_id.name,
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.bank_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'credit': rec.preliminary_gurantee_amount + rec.bank_commission,
                    'debit': 0.0,
                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.project_id.bank_commission.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': 0.0,
                    'debit': rec.bank_commission,
                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.project_id.preliminary_guarantee.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': 0.0,
                    'debit': rec.preliminary_gurantee_amount,

                })
            rec.status = 'confirmed'
            rec.move_id = move.id
