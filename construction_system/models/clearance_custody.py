# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class ProjectClearance(models.Model):
    _name = 'clearance.custody'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("clearance NO", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                             default='draft')
    employee_id = fields.Many2one('hr.employee', 'Employee Name')
    date = fields.Date('Date',default=datetime.today())
    custody_id = fields.Many2one('project.custody', string='Custody Transaction')
    employee_account_id = fields.Many2one('account.account', string='Employee Custody Account')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    amount = fields.Float('Open Amount', compute='compute_amount')
    cleared_amount = fields.Float('Cleared Amount', compute='compute_cleared_amount')
    line_ids = fields.One2many(comodel_name="clearance.custody.line", inverse_name="clearance_id", string="line_ids", )
    move_ids = fields.One2many(comodel_name="clearance.move.line", inverse_name="clearance_id", string="line_ids", )


    @api.constrains('custody_id')
    def _constrains(self):
        for rec in self:
            custody=self.env['clearance.custody'].search([('custody_id','=',rec.custody_id.id)])
            total_amount = 0.0
            for cu in custody:
                for line in cu.line_ids:
                    total_taxs = 0.0
                    for tax in line.invoice_line_tax_id:
                        total_taxs += tax.amount * line.amount
                    total_amount += line.amount + total_taxs
            if total_amount >= rec.custody_id.amount:
                raise UserError( _('The Cleared Amount Is Over Custody Amount'))


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        res = {}
        cust = []
        if self.employee_id:
            custudy = self.env['project.custody'].search([('employee_id', '=', self.employee_id.id)])
            for cu in custudy:
                cust.append(cu.id)
            if len(cust)>0:
                res['domain'] = {'custody_id': [('id', 'in', cust)]}

            else:
                res['domain'] = {'custody_id': [('id', '=', False)]}
        return res


    @api.onchange('custody_id', 'project_id', 'employee_account_id')
    @api.constrains('custody_id')
    def _onchange_custody_id(self):
        for rec in self:
            rec.project_id = rec.custody_id.project_id.id
            rec.employee_account_id = rec.custody_id.debit_account_id.id


    @api.depends('line_ids.amount')
    def compute_cleared_amount(self):
        for rec in self:
            tax_amount=0.0
            amount_tot = sum(x.amount for x in rec.line_ids)
            for line in rec.line_ids:
                for tax in line.invoice_line_tax_id:
                    tax_amount += line.amount * tax.amount
            rec.cleared_amount=tax_amount+amount_tot




    @api.depends('custody_id')
    def compute_amount(self):
        for rec in self:
            custody_ids = self.env['clearance.custody'].search([('employee_id', '=', rec.employee_id.id),
                                  ('project_id', '=', rec.project_id.id),('custody_id', '=', rec.custody_id.id)])
            amount = 0.0
            tax_amount = 0.0
            for custody in custody_ids:
                for line in custody.line_ids:
                    for tax in line.invoice_line_tax_id:
                        tax_amount += line.amount*tax.amount
                    amount += line.amount
            rec.amount = rec.custody_id.amount - amount-tax_amount


    def confirm_quotation(self):
        for rec in self:
            for line in rec.line_ids:
                move = self.env['account.move'].create({
                    'journal_id': line.journal_id.id,
                    'date': rec.date,
                    'project_id': rec.project_id.id,
                })
                if line.expenses_account_id:
                    if line.invoice_line_tax_id:
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': rec.employee_account_id.id,
                                'name': line.desc,
                                # 'analytic_account_id':line.project_id.analytic_account_id.id,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'credit': line.amount+ line.invoice_line_tax_id.amount*line.amount,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.expenses_account_id.id,
                                'analytic_account_id': line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.amount,
                                'partner_id': line.partner_id.id,

                            })
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.invoice_line_tax_id.account_collected_id.id,
                                # 'analytic_account_id':line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.invoice_line_tax_id.amount*line.amount,
                                'partner_id': line.partner_id.id,

                            })
                        self.env['clearance.move.line'].create({
                            'clearance_id': self.id,
                            'move_id': move.id,
                        })

                        self.env['project.clearance.line'].create({
                            'cust_id': rec.custody_id.id,
                            'amount': line.amount,
                            'desc': line.desc,
                            'partner_id': line.partner_id.id,
                            'invoice_no': line.invoice_no,
                            # 'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                            'project_id': line.project_id.id,
                            'product_id': line.product_id.id,
                            'journal_id': line.journal_id.id,
                            'expenses_account_id': line.expenses_account_id.id,
                            'general_account_id': line.general_account_id.id,
                        })
                    else:

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': rec.employee_account_id.id,
                                'name': line.desc,
                                # 'analytic_account_id': line.project_id.analytic_account_id.id,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'credit': line.amount,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.expenses_account_id.id,
                                'analytic_account_id':line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.amount,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['clearance.move.line'].create({
                            'clearance_id': self.id,
                            'move_id': move.id,
                        })
                        self.env['project.clearance.line'].create({
                            'cust_id': rec.custody_id.id,
                            'amount': line.amount,
                            'desc': line.desc,
                            'partner_id': line.partner_id.id,
                            'invoice_no': line.invoice_no,
                            'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                            'project_id': line.project_id.id,
                            'product_id': line.product_id.id,
                            'journal_id': line.journal_id.id,
                            'expenses_account_id': line.expenses_account_id.id,
                            'general_account_id': line.general_account_id.id,
                        })

                else:
                    if line.invoice_line_tax_id:
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': rec.employee_account_id.id,
                                'name': line.desc,
                                # 'analytic_account_id':line.project_id.analytic_account_id.id,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'credit': line.amount+ line.invoice_line_tax_id.amount*line.amount,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.general_account_id.id,
                                'analytic_account_id': line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.amount,
                                'partner_id': line.partner_id.id,

                            })
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.invoice_line_tax_id.account_collected_id.id,
                                'analytic_account_id':line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.invoice_line_tax_id.amount*line.amount,
                                'partner_id': line.partner_id.id,

                            })
                        self.env['clearance.move.line'].create({
                            'clearance_id': self.id,
                            'move_id': move.id,
                        })
                        self.env['project.clearance.line'].create({
                            'cust_id': rec.custody_id.id,
                            'amount': line.amount,
                            'desc': line.desc,
                            'partner_id': line.partner_id.id,
                            'invoice_no': line.invoice_no,
                            'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                            'project_id': line.project_id.id,
                            'product_id': line.product_id.id,
                            'journal_id': line.journal_id.id,
                            'expenses_account_id': line.expenses_account_id.id,
                            'general_account_id': line.general_account_id.id,
                        })
                    else:

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': rec.employee_account_id.id,
                                'name': line.desc,
                                # 'analytic_account_id':line.project_id.analytic_account_id.id,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'credit': line.amount ,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {
                                'move_id': move.id,
                                'account_id': line.general_account_id.id,
                                'analytic_account_id': line.project_id.analytic_account_id.id,
                                'name': line.desc,
                                'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                                'debit': line.amount,
                                'partner_id': line.partner_id.id,

                            })

                        self.env['clearance.move.line'].create({
                            'clearance_id': self.id,
                            'move_id': move.id,
                        })
                        self.env['project.clearance.line'].create({
                            'cust_id': rec.custody_id.id,
                            'amount': line.amount,
                            'desc': line.desc,
                            'partner_id': line.partner_id.id,
                            'invoice_no': line.invoice_no,
                            'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                            'project_id': line.project_id.id,
                            'product_id': line.product_id.id,
                            'journal_id': line.journal_id.id,
                            'expenses_account_id': line.expenses_account_id.id,
                            'general_account_id': line.general_account_id.id,
                        })

            rec.state = 'confirmed'
            # rec.move_id = move.id
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('clearance.custody')
        vals['number'] = sequence or '/'
        return super(ProjectClearance, self).create(vals)


class ProjectClearanceLine(models.Model):
    _name = 'clearance.custody.line'
    clearance_id = fields.Many2one('clearance.custody', string='clearance')
    amount = fields.Float('Amount', )
    desc = fields.Char('Desc', )
    partner_id = fields.Many2one("res.partner", 'partner',)
    invoice_no = fields.Char('Inv No', )
    # tax_no=fields.Char(related='partner_id.',string='Tax No',)
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    product_id = fields.Many2one(comodel_name="product.product", string="Product", )
    journal_id = fields.Many2one('account.journal', string='Journal')
    expenses_account_id = fields.Many2one('account.account', string='Expense Account')
    general_account_id = fields.Many2one('account.account', string='General Account')

    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     for rec in self:
    #         rec.expenses_account_id = rec.product_id.property_account_expense.id


class ProjectMoveLine(models.Model):
    _name = 'clearance.move.line'
    clearance_id = fields.Many2one('clearance.custody', string='clearance')
    move_id = fields.Many2one(comodel_name="account.move", string="Journal Entry", )
