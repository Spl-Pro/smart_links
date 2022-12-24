# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from datetime import datetime


class SubContractRFQ(models.Model):
    _name = 'subcontract.rfq'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Request For Quotation", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                             default='draft')
    partner_id = fields.Many2one('res.partner', string='Supplier', )
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    date = fields.Date('Order Date',default=datetime.today())
    location_id = fields.Many2one('stock.location', string="Deliver To")

    rfq_lines_ids = fields.One2many(comodel_name="subcontract.rfq.line", inverse_name="rfq_id",
                                    string="Bid Requirments", )
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                                  store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_tax')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount')
    # tax_line = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines',
    #                            readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    is_confirmed = fields.Boolean('Confirmed')


    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('sub.contract.agreement')
        vals['number'] = sequence or '/'
        return super(SubContractRFQ, self).create(vals)

    def confirm_order(self):
        for rec in self:
            agreement = self.env['sub.contract.agreement'].create({
                'partner_id': rec.partner_id.id,
                'project_id': rec.project_id.id,
                'date': rec.date,
            })
            for line in rec.rfq_lines_ids:
                rec.env['work.line'].create({
                    'task_id': agreement.id,
                    'wcateg_id': line.wcateg_id.id,
                    'product_id': line.product_id.id,
                    'unit_price': line.unit_price,
                    'qty': line.qty,
                    'invoice_line_tax_id': [(6, 0, line.invoice_line_tax_id.ids)],
                    'amount': line.sales_amount,
                })
            rec.state = 'confirmed'

    @api.depends('rfq_lines_ids.sales_amount', )
    def _compute_tax(self):
        for rec in self:
            if rec.rfq_lines_ids:
                rec.amount_tax =0.0
                rec.amount_tax = sum(x.amount_tax for x in rec.rfq_lines_ids)

    # @api.depends('rfq_lines_ids.sales_amount', 'tax_line.amount')
    @api.depends('rfq_lines_ids.sales_amount',)
    def _compute_amount(self):
        for rec in self:
            rec.amount_untaxed = sum(line.sales_amount for line in rec.rfq_lines_ids)
            rec.amount_tax = sum(x.amount_tax for x in rec.rfq_lines_ids)
            self.amount_total = rec.amount_untaxed + rec.amount_tax


class QuotationBid(models.Model):
    _name = 'subcontract.rfq.line'

    rfq_id = fields.Many2one(comodel_name="subcontract.rfq", string="RFQ", )
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    date = fields.Date('Schedual Date')
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account')
    qty = fields.Float('Quantity',default=1.0)
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    unit_price = fields.Float('Unit Price', )
    sales_amount = fields.Float('Subtotal', compute='_Compute_sales_amount')
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    amount_tax = fields.Float('Amount',compute='_compute_amount_tax')

    @api.onchange('wcateg_id')
    def _onchange_project_id_categ(self):
        for rec in self:
            res = {}
            require_ids = []
            for line in rec.rfq_id.project_id.bid_requirement_ids:
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
            for line in rec.rfq_id.project_id.bid_requirement_ids:
                if rec.wcateg_id and rec.wcateg_id == line.wcateg_id:
                    work_item_ids.append(line.product_id.id)
            if len(work_item_ids) > 0:
                res['domain'] = {'product_id': [('id', 'in', work_item_ids)]}
            else:
                res['domain'] = {'product_id': [('id', '=', False)]}
            return res

    @api.depends('unit_price', 'qty')
    def _Compute_sales_amount(self):
        for rec in self:
            amount_tax = 0.0
            rec.sales_amount = rec.unit_price * rec.qty

    @api.depends('invoice_line_tax_id', 'sales_amount')
    def _compute_amount_tax(self):
        for rec in self:
            rec.amount_tax = 0.0
            amount_tax = 0.0
            if rec.invoice_line_tax_id:
                for line in rec.invoice_line_tax_id:
                    amount_tax =amount_tax + (rec.unit_price *rec.qty * line.amount)/100
                    rec.amount_tax = amount_tax
