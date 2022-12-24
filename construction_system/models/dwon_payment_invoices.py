# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class DownPayment(models.Model):
    _name = 'down.payment'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Down Payment ID", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             default='draft')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    date = fields.Date('Date', default=datetime.today())
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer", domain=[('customer', '=', True)])
    project_value = fields.Float('Project Value', related='project_id.total_cost')
    payment_method = fields.Selection(string="Payment Method", selection=[('cash', 'Cash'), ('cheque', 'Cheque'),
                                                                          ('transfer', 'Transfer'), ], default='cash')
    down_payment_per = fields.Float('Down Payment %', readonly=True)
    down_payment_value = fields.Float('Down Payment Value')
    journal_id = fields.Many2one('account.journal', string='Journal')
    payment_term_id = fields.Many2one(comodel_name="account.payment.term", string="Payment Term", required=False, )
    invoice_id = fields.Many2one('account.move', string="Down Payment Invoice")
    note = fields.Text('Description')

    @api.onchange('project_id')
    @api.constrains('project_id')
    def _onchange_project_id_contract(self):
        for rec in self:
            if self.project_id:
                contract = self.env['project.contract'].search([('project_id', '=', rec.project_id.id)])
                rec.down_payment_per = contract.down_payment_per
                rec.down_payment_value = rec.project_value * rec.down_payment_per / 100

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            down = self.env['down.payment'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if down:
                raise UserError(_('This Project Has Down Payment'))

            contract = self.env['project.contract'].search([('project_id', '=', self.project_id.id)])
            if contract:
                pass
            else:
                raise UserError(_('This Project Must Has Contract'))

    def set_to_draft(self):
        for rec in self:
            rec.state = 'draft'


    def down_payment(self):
        for rec in self:
            x = 0.0
            for pay in rec.payment_term_id.line_ids:
                x = pay.days
            tax_ids = self.env['account.tax'].search([('is_default', '=', True)])

            if rec.project_id.down_payment_account:
                move = self.env['account.move'].sudo().create({
                    'partner_id': rec.partner_id.id,
                    'move_type': 'out_invoice',
                    'project_id': rec.project_id.id,
                    'journal_id': rec.journal_id.id,
                    'invoice_date': rec.date,
                })
                self.env['account.move.line'].with_context(
                    check_move_validity=False).create({
                    'move_id': move.id,
                    'name': 'Down Payment',
                    'quantity': 1,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'account_id': rec.project_id.down_payment_account.id,
                    'price_unit': rec.project_value * rec.down_payment_per / 100
                })
            else:
                raise (_('You Must Choose Project Down Payment Account'))
            rec.invoice_id = move.id
            rec.state = 'confirmed'

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('down.payment')
        vals['number'] = sequence or '/'
        return super(DownPayment, self).create(vals)
