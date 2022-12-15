# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime

class ProjectCustody(models.Model):
    _name = 'project.custody'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Custody Number", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                              default='draft')
    employee_id=fields.Many2one('hr.employee','Employee Name')
    date=fields.Date('Date',default=datetime.today())
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    journal_id=fields.Many2one('account.journal',string='Journal')
    amount=fields.Float('Amount')
    open_amount=fields.Float('Open Amount',compute='_compute_sum')
    cleared_amount=fields.Float('Expense Amount', compute='_compute_sum')
    sum_tax=fields.Float('Sum Tax', compute='_compute_sum')
    total_cleared=fields.Float('Cleared Amount', compute='_compute_sum')
    credit_account_id=fields.Many2one('account.account',string='Credit Account')
    debit_account_id=fields.Many2one('account.account',string='Debit Account')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    payment_method = fields.Selection(string="Payment Method", selection=[('cash', 'Cash'), ('cheque', 'Cheque'),
                                                                 ('transfer', 'Transfer'), ], default='cash')
    clearance_line_ids = fields.One2many(comodel_name="project.clearance.line", inverse_name="cust_id", string="cust_id", )
    ref = fields.Char('Ref')

    note=fields.Text('Description')


    @api.depends('clearance_line_ids',)
    def _compute_sum(self):
        for rec in self:
            tax = 0.0
            expense = 0.0
            for line in rec.clearance_line_ids:
                expense=expense+line.amount
                if line.invoice_line_tax_id:
                    for taxs in line.invoice_line_tax_id:
                        tax += (taxs.amount*line.amount)
                    rec.sum_tax=tax
            rec.cleared_amount=expense
            rec.total_cleared= rec.cleared_amount+rec.sum_tax
            rec.open_amount= rec.amount - rec.total_cleared

    @api.depends('amount',)
    def _compute_cleared_amount(self):
        for rec in self:
            custody_ids = self.env['clearance.custody'].search([('employee_id', '=', rec.employee_id.id),
                                 ('custody_id', '=', rec.id), ('project_id', '=', rec.project_id.id)])
            amount = 0.0
            for custody in custody_ids:
                for line in custody.line_ids:
                    amount += line.amount
            rec.cleared_amount = amount
            rec.open_amount = rec.amount - rec.cleared_amount


    # @api.one
    # @api.depends('amount','cleared_amount')
    # def compute_open_amount(self):
    #     for rec in self:
    #         rec.open_amount = rec.amount - rec.cleared_amount


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
                    'account_id': rec.credit_account_id.id,
                    'name': rec.project_id.name,
                    'credit': rec.amount,

                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.debit_account_id.id,
                    'name': rec.project_id.name,
                    'debit': rec.amount,
                })

            rec.state = 'confirmed'
            rec.move_id = move.id
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('project.custody')
        vals['number'] = sequence or '/'
        return super(ProjectCustody, self).create(vals)


class ProjectCustodyLine(models.Model):
    _name = 'project.clearance.line'
    cust_id = fields.Many2one(comodel_name="project.custody", string="Custody",)
    amount = fields.Float('Amount', )
    desc = fields.Char('Desc', )
    partner_id = fields.Many2one("res.partner", 'partner', domain=[('supplier', '=', True)])
    invoice_no = fields.Char('Inv No', )
    # tax_no=fields.Char(related='partner_id.',string='Tax No',)
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    project_id = fields.Many2one('project.project', string='Project')
    product_id = fields.Many2one(comodel_name="product.product", string="Product", )
    journal_id = fields.Many2one('account.journal', string='Journal')
    expenses_account_id = fields.Many2one('account.account', string='Expense Account')
    general_account_id = fields.Many2one('account.account', string='General Account')
