# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime

class RetentionClaim(models.Model):
    _name = 'retention.claim'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Number", readonly=True)
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                             default='draft')
    date = fields.Date('Date', default=datetime.today())
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer')
    bank_account_id = fields.Many2one('account.account', string='Bank Account')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    note = fields.Text('Description')
    amount =fields.Float('Amount')
    # amount =fields.Float('Amount',compute='_compute_retention_amount')

    # @api.one
    # @api.depends('project_id')
    # def _compute_retention_amount(self):
    #     for rec in self:
    #         rec.amount =0.0
    #         account_move=self.env['account.move'].search([('project_id','=',self.project_id.id)])
    #         for line in account_move:
    #             x = 0.0
    #             for moves in line.line_id:
    #                 if moves.account_id==self.project_id.retention_account and moves.credit==0.0:
    #                     x = x+ moves.debit
    #             rec.amount = x

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('retention.claim')
        vals['number'] = sequence or '/'
        return super(RetentionClaim, self).create(vals)



    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            preliminary = self.env['retention.claim'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if preliminary:
                raise UserError( _('You Have Retention Claim For This Project'))

    def set_to_draft(self):
        self.status='draft'
    def confirm_quotation(self):
        for rec in self:
            move = self.env['account.move'].create({
                'journal_id': rec.journal_id.id,
                'date': rec.date,
                # 'move_type':'out_invoice',
                'project_id': rec.project_id.id,
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.bank_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    # 'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'debit': rec.amount,
                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.project_id.retention_account.id,
                    # 'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': rec.amount,

                })
            rec.status = 'confirmed'
            rec.move_id = move.id