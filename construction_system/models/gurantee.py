# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime

class FinalGurantee(models.Model):
    _name='final.gurantee'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Transaction Number", readonly=True)
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                              default='draft')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer')
    bank_account_id = fields.Many2one('account.account', string='Bank Account')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    date = fields.Date('Date', default=datetime.today())
    final_gurantee_per = fields.Float('Finanl Gurantee Percentage % ',compute='compute_final_gurantee')
    final_gurantee_amount = fields.Float('Finanl Gurantee Amount ',compute='compute_final_gurantee')
    total_amount = fields.Float('Total Amount',compute='compute_final_gurantee')
    bank_commission = fields.Float('Bank Commission')
    note = fields.Text('Description')

    @api.depends('project_id')
    def compute_final_gurantee(self):
        self.total_amount =0.0
        contract = self.env['project.contract'].search([('project_id', '=', self.project_id.id)])
        for rec in contract:
            self.final_gurantee_per = rec.final_gurantee
            self.total_amount =self.project_id.total_cost
        self.final_gurantee_amount = self.project_id.total_cost * (self.final_gurantee_per) / 100

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            contract = self.env['final.gurantee'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if contract:
                raise UserError(_('This Project Has another Final Gurantee'))

    def set_to_draft(self):
        for rec in self:
            rec.status = 'draft'
    def confirm_quotation(self):
        for rec in self:
            move = self.env['account.move'].create({
                'journal_id': rec.journal_id.id,
                'date': rec.date,
                'project_id': rec.project_id.id,
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.bank_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'credit': rec.final_gurantee_amount + rec.bank_commission,
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
                    'account_id': rec.project_id.final_guarantee.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': 0.0,
                    'debit': rec.final_gurantee_amount,

                })
            rec.status = 'confirmed'
            rec.move_id = move.id

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('final.gurantee')
        vals['number'] = sequence or '/'
        return super(FinalGurantee, self).create(vals)