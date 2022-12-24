# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime

class SubContractAgrement(models.Model):
    _name='sub.contract.agreement'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    number = fields.Char("Sub-Contracting Agrement", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                             default='draft')
    partner_id = fields.Many2one('res.partner',string='Sub Contractor')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    date = fields.Date('Date',default=datetime.today())
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    retention_per = fields.Float('Retention %')
    down_payment_per = fields.Float('Down Payment %')
    payment_term_id = fields.Many2one(comodel_name="account.payment.term", string="Payment Term", required=False, )
    is_down_payment = fields.Boolean('Is Down')
    is_project_invoice = fields.Boolean('Is Down')
    invoice_id = fields.Many2one('account.move', string="Down Payment Invoice")
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                                  store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
                              store=True, readonly=True, compute='_compute_tax')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount')
    # tax_line = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines',
    #                            readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    work_lines_ids = fields.One2many(comodel_name="work.line", inverse_name="task_id", string="", required=False, )


    @api.depends('work_lines_ids.amount_tax', )
    def _compute_tax(self):
        for rec in self:
            rec.amount_tax = sum(x.amount_tax for x in rec.work_lines_ids)

    @api.depends('work_lines_ids.amount',)
    def _compute_amount(self):
        self.amount_untaxed = sum(line.amount for line in self.work_lines_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax

    def approve(self):
        for rec in self:
            rec.state = 'confirmed'

    def down_payment(self):
        for rec in self:
            if rec.down_payment_per >0:
                journal_id=self.env['account.journal'].search([('type','=','purchase')],limit=1)
                account_id = self.env['account.move'].create({
                    'partner_id': rec.partner_id.id,
                    'project_id': rec.project_id.id,
                    # 'account_id': rec.partner_id.property_account_payable_id.id,
                    'invoice_date': rec.date,
                    'ref': rec.number,
                    'journal_id': journal_id.id,
                    'move_type': 'in_invoice',
                })
                for line in rec.work_lines_ids:
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': account_id.id,
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'quantity': 1,
                        # 'tax_ids': [(6, 0, line.invoice_line_tax_id.ids)],
                        'account_id': line.product_id.property_account_income_id.id,
                        'price_unit': (line.qty * line.unit_price)*rec.down_payment_per/100,
                    })
            else:
                raise UserError (_('You Must Enter Down Payment Amount'))
            rec.invoice_id = account_id.id
            rec.is_down_payment = True

    def view_down_payment(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'account invoice',
                'view_type': 'form',
                'view_id': self.env.ref('account.view_move_form').id,
                'domain': [('type', '=', 'in_invoice')],
                'res_id': rec.invoice_id.id,
                'view_mode': 'form',
                'res_model': 'account.move',
                'target': 'current',
            }

    def create_planning_invoices(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'account invoice',
                'view_type': 'form',
                'view_id': self.env.ref('account.view_move_form').id,
                'domain': [('type', '=', 'in_invoice')],
                'res_id': False,
                'view_mode': 'form',
                'res_model': 'account.move',
                'context': {'default_partner_id': rec.partner_id.id,
                            'default_project_id': rec.project_id.id,
                            'default_account_id': rec.partner_id.property_account_payable_id.id,
                            'default_journal_id': self.env['account.journal'].search([('type','=','purchase')],limit=1).id,
                            'default_origin': rec.number,
                            'default_date_invoice': rec.date,
                            'default_type': 'in_invoice',
                            'default_is_project_invoice': True,
                            },
                'target': 'current',
            }

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('sub.contract.agreement')
        vals['number'] = sequence or '/'
        return super(SubContractAgrement, self).create(vals)

class MaterialTask(models.Model):
    _name = 'work.line'
    task_id = fields.Many2one(comodel_name="sub.contract.agreement", string="Project task", )
    subcontracted = fields.Boolean('Subcontracted',default=True)
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    description = fields.Char(related='product_id.name', string='Description')
    qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    unit_price = fields.Float(' Unit Price')
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    amount_tax = fields.Float('Amount',compute='_compute_amount_tax')
    amount = fields.Float('Amount', compute='_Compute_amount')

    @api.onchange('wcateg_id')
    def _onchange_wcateg_id(self):
        res = {}
        require_ids = []
        for rec in self:
            for line in rec.task_id.project_id.bid_requirement_ids:
                require_ids.append(line.wcateg_id.id)
            if len(require_ids) > 0:
                res['domain'] = {'wcateg_id': [('id', 'in', require_ids)]}
            else:
                res['domain'] = {'wcateg_id': [('id', '=', False)]}
        return res

    @api.onchange('wcateg_id')
    def _onchange_product_id(self):
        res = {}
        require_ids = []
        for rec in self:
            for line in rec.task_id.project_id.bid_requirement_ids:
                if line.wcateg_id == rec.wcateg_id:
                    require_ids.append(line.product_id.id)
            if len(require_ids) > 0:
                res['domain'] = {'product_id': [('id', 'in', require_ids)]}
            else:
                res['domain'] = {'product_id': [('id', '=', False)]}
        return res

    @api.depends('invoice_line_tax_id', 'amount')
    def _compute_amount_tax(self):
        for rec in self:
            amount_tax = 0.0
            rec.amount_tax = 0.0
            for line in rec.invoice_line_tax_id:
                amount_tax += (rec.amount * line.amount/100)
                rec.amount_tax = amount_tax

    @api.depends('unit_price', 'qty')
    def _Compute_amount(self):
        for rec in self:
            rec.amount = rec.qty * rec.unit_price
