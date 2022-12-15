# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class DownPayment(models.Model):
    _name = 'progress.bill.invoice'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Progress Billing No", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved'),
                                                         ('invoice_created', 'Invoice Created')], default='draft')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    date = fields.Date('Date',default=datetime.today())
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer", domain=[('customer', '=', True)])
    customer_type = fields.Selection(string="", related='project_id.customer_type', required=False, )

    invoiced_amount = fields.Float('Invoiced Amount')
    invoice_amount = fields.Float('Invoice Amount')
    payment_term_id = fields.Many2one(comodel_name="account.payment.term", string="Payment Term", required=False, )

    retention_per = fields.Float('Retention %', compute='_compute_contract', store=True)
    down_payment_per = fields.Float('Down Payment %', compute='_compute_contract', store=True)
    retention_deduction = fields.Float('Retention Deduction', compute='_compute_deduction')
    down_payment_deduction = fields.Float(' Down Payment Deduction', compute='_compute_deduction')
    down_payment_invioce = fields.Many2one('account.move', string="Down Payment Invoice",
                                           compute='compute_down_invoice')
    invoice_id = fields.Many2one(comodel_name="account.move", string="Invoice Number")
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                                  store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_tax')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount')
    # tax_line = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines',
    #                            readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    bill_invoice_ids = fields.One2many(comodel_name="progress.bill.invoice.line", inverse_name="bill_invoice_id",
                                       string="Bid Requirments", )
    is_contract = fields.Boolean('Contract')

    @api.depends('project_id')
    def _compute_deduction(self):
        for rec in self:
            rec.retention_deduction = sum(l.sales_amount for l in rec.bill_invoice_ids)*rec.retention_per/100
            rec.down_payment_deduction =sum(l.sales_amount for l in rec.bill_invoice_ids)* rec.down_payment_per / 100

    @api.depends('project_id')
    def compute_down_invoice(self):
        for rec in self:
            down = self.env['down.payment'].search([('project_id', '=', rec.project_id.id)])
            rec.down_payment_invioce = down.invoice_id
            rec.payment_term_id =rec.partner_id.property_payment_term_id

    @api.depends('project_id')
    def _compute_contract(self):
        for rec in self:
            contract = self.env['project.contract'].search([('project_id', '=', rec.project_id.id)])
            rec.down_payment_per = contract.down_payment_per
            rec.retention_per = contract.retention_per
            rec.is_contract = True

    @api.depends('bill_invoice_ids.amount_tax', )
    def _compute_tax(self):
        for rec in self:
            rec.amount_tax =0.0
            rec.amount_tax = sum(x.amount_tax for x in rec.bill_invoice_ids)
            # rec.amount_tax = 0.0

    # @api.depends('bill_invoice_ids.sales_amount', 'tax_line.amount')
    @api.depends('bill_invoice_ids.sales_amount',)
    def _compute_amount(self):
        pass
    #     self.amount_untaxed = sum(line.sales_amount for line in self.bill_invoice_ids)
    #     self.amount_total = self.amount_untaxed

    def confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def create_invoice(self):
        for rec in self:
            x=0.0
            for pay in rec.payment_term_id.line_ids:
                x=pay.days
            account_id = self.env['account.move'].create({
                'partner_id': rec.partner_id.id,
                'project_id': rec.project_id.id,
                # 'account_id': rec.partner_id.property_account_receivable_id.id,
                'invoice_date': rec.date,
                'progress_id': rec.id,
                'invoice_date_due': datetime.strptime(str(self.date), '%Y-%m-%d')+relativedelta(days =+ x),
                'move_type': 'out_invoice',
                'is_project_invoice': True,
            })
            if rec.retention_per:
                for line in rec.bill_invoice_ids:
                    self.env['account.move.line'].with_context(
                    check_move_validity=False).create({
                        'move_id': account_id.id,
                        'product_id': line.product_id.id,
                        'account_id': rec.project_id.income_account.id,
                        'name': line.description,
                        'quantity': line.qty,
                        'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                        # 'account_analytic_id': rec.project_id.analytic_account_id.id,
                        'price_unit': (
                        (line.sales_price * line.qty) - (line.sales_price * (100 - line.achievement_rate) / 100) - (
                            ((line.sales_price * line.qty) - (line.sales_price * (100 - line.achievement_rate) / 100)) * (rec.retention_per) / 100) - (
                            ((line.sales_price * line.qty) - (line.sales_price * (100 - line.achievement_rate) / 100)) * (rec.down_payment_per) / 100))

                    })
            else:
                for line in rec.bill_invoice_ids:
                    self.env['account.move.line'].with_context(
                    check_move_validity=False).create({
                        'invoice_id': account_id.id,
                        'account_id': rec.project_id.income_account.id,
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'quantity': line.qty,
                        'invoice_line_tax_id': [(6, 0, line.invoice_line_tax_id.ids)],
                        'account_analytic_id': rec.project_id.analytic_account_id.id,
                        'price_unit':  (
                        (line.sales_price * line.qty) - (line.sales_price * (100 - line.achievement_rate) / 100) - (
                            ((line.sales_price * line.qty) - (line.sales_price * (100 - line.achievement_rate) / 100)) * (rec.down_payment_per) / 100))

                    })
            rec.invoice_id = account_id.id
            rec.state = 'invoice_created'
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('progress.bill.invoice')
        vals['number'] = sequence or '/'
        return super(DownPayment, self).create(vals)


class ProgressBinvLine(models.Model):
    _name = 'progress.bill.invoice.line'

    bill_invoice_id = fields.Many2one(comodel_name="progress.bill.invoice", string="Project", )
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    description = fields.Char(related='product_id.name', string='Description')
    qty = fields.Float('Quantity', default=1.0)
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    achievement_rate = fields.Float('Achievement Rate %', )
    sales_price = fields.Float('Sales Price', )
    sales_amount = fields.Float('Amount', compute='_Compute_sales_amount')
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    amount_tax = fields.Float('Amount', compute='compute_amount_tax')

    @api.onchange('wcateg_id')
    def _onchange_project_id_categ(self):
        for rec in self:
            res = {}
            require_ids = []
            for line in rec.bill_invoice_id.project_id.bid_requirement_ids:
                require_ids.append(line.wcateg_id.id)
            if len(require_ids) > 0:
                res['domain'] = {'wcateg_id': [('id', 'in', require_ids)]}
            else:
                res['domain'] = {'wcateg_id': [('id', '=', False)]}
            return res

    @api.onchange('wcateg_id', 'product_id')
    def _onchange_partner_id_categ(self):
        for rec in self:
            res = {}
            work_item_ids = []
            for line in rec.bill_invoice_id.project_id.bid_requirement_ids:
                if rec.wcateg_id and rec.wcateg_id == line.wcateg_id:
                    work_item_ids.append(line.product_id.id)
            if len(work_item_ids) > 0:
                res['domain'] = {'product_id': [('id', 'in', work_item_ids)]}
            else:
                res['domain'] = {'product_id': [('id', '=', False)]}
            return res

    @api.onchange( 'product_id','wcateg_id')
    def _onchange_product_id(self):
        for rec in self:
            quotation=self.env['project.quotation'].search([('project_id','=',rec.bill_invoice_id.project_id.id)])
            for line in quotation.bid_requirement_ids:
                if rec.product_id ==line.product_id and  rec.wcateg_id ==line.wcateg_id:
                    rec.sales_price = line.sales_price
                    rec.invoice_line_tax_id = line.invoice_line_tax_id



    @api.depends('invoice_line_tax_id', 'sales_amount')
    def compute_amount_tax(self):
        for rec in self:
            rec.amount_tax = 0.0
            amount_tax = 0.0
            for line in rec.invoice_line_tax_id:
                amount_tax += (rec.sales_amount * line.amount)
                rec.amount_tax = amount_tax

    @api.depends('sales_price', 'achievement_rate', 'qty')
    def _Compute_sales_amount(self):
        for rec in self:
            # x=0.0
            # if rec.achievement_rate ==100:
            #     x=rec.sales_price
            # else:
            x=(rec.sales_price * (rec.achievement_rate) / 100)
            rec.sales_amount = (x * rec.qty)
class AccountInvoice(models.Model):
    _inherit = 'account.move'
    planning_id = fields.Many2one(comodel_name="project.planning", string="Project Planning", )
    progress_id = fields.Many2one(comodel_name="progress.bill.invoice", string="Project Progress Invoice", )
    project_id = fields.Many2one(comodel_name="project.project", string="Project ", domain=[('awarded', '=', True)])
    account_journal_2 = fields.Many2one(comodel_name="account.move", string="Journal Entry 2", )
    is_project_invoice = fields.Boolean('Down Payment')

    def invoice_validate(self):
        for rec in self:
            res = super(AccountInvoice, self).invoice_validate()
            rec.move_id.project_id =rec.project_id.id
            for line in  rec.move_id.line_id:
                pass
                # line.analytic_account_id= rec.project_id.analytic_account_id.id,
            if rec.is_project_invoice:
                vals = []
                vals.append(
                    (0, 0, {
                        'account_id': rec.project_id.income_account.id,
                        'date': self.date_invoice,
                        'name': 'Down Payment and retention',
                        # 'credit': contract.retention_per/100*rec.progress_id. + contract.down_payment_per/100*rec.amount_untaxed,
                        'credit': rec.progress_id.retention_deduction+ rec.progress_id.down_payment_deduction,
                    }))
                vals.append(
                    (0, 0, {
                        'account_id': rec.project_id.retention_account.id,
                        'date': self.date_invoice,
                        'name': " retention",
                        # 'debit':50,
                        'debit':rec.progress_id.retention_deduction,
                    }))
                vals.append(
                    (0, 0, {
                        'account_id': rec.project_id.down_payment_account.id,
                        'date': self.date_invoice,
                        'name': 'Down payment',
                        'invoice': self.id,
                        # 'debit': 50,
                        'debit': rec.progress_id.down_payment_deduction,
                    }))

                move_id = self.env['account.move'].create({
                    'journal_id': rec.journal_id.id,
                    'project_id': rec.project_id.id,
                    'ref': rec.number,
                    'line_id': vals,
                })
                rec.account_journal_2 = move_id.id

                move_id.post()
            return res