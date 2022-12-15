# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import odoo.addons.decimal_precision as dp
from datetime import datetime


class ProjectQuotation(models.Model):
    _name = 'project.quotation'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    number = fields.Char("Project Quotation ", readonly=True)
    state = fields.Selection(string="", selection=[('win', 'Won'), ('lost', 'Lost'), ],)
    status = fields.Selection(string="Status", selection=[('draft', 'Quotation'), ('confirmed', 'Confirm Quotation'), ('sale_order', 'Sale Order')],default='draft' )
    project_id = fields.Many2one(comodel_name="project.project", string="Project", )
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer", )
    customer_type = fields.Selection(string="", related='project_id.customer_type',)
    expire_date = fields.Datetime('Expiry Date')
    date = fields.Datetime('Date',default=datetime.today())
    ref = fields.Char('Reference/Description')
    preliminary_gurantee = fields.Many2one('preliminary.gurantee', 'Preliminary Gurantee')
    bid_requirement_ids = fields.One2many(comodel_name="quotation.bid.requirement", inverse_name="quotation_id",
                                          string="Bid Requirments", )
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
                                  store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
                               readonly=True, compute='_compute_tax')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
                                store=True, readonly=True, compute='_compute_amount')
    is_contract = fields.Boolean('contract')


    def create_contract(self):
        contract =self.env['project.contract'].create({
            'project_id':self.project_id.id,
            'partner_id':self.partner_id.id,
            'date':self.date,
        })
        self.is_contract =True

    @api.onchange('project_id')
    def _onchange_preliminary_gurantee(self):
        res = {}
        for rec in self:
            pre=self.env['preliminary.gurantee'].search([('project_id','=',rec.project_id.id)])
            if len(pre.ids) > 0:
                res['domain'] = {'preliminary_gurantee': [('id', 'in', pre.ids)]}
            else:
                res['domain'] = {'preliminary_gurantee': [('id', '=', False)]}
        return res

    def _find_mail_template(self, force_confirmation_template=False):
        template_id = False

        if force_confirmation_template or (self.state == 'sale' and not self.env.context.get('proforma', False)):
            template_id = int(self.env['ir.config_parameter'].sudo().get_param('sale.default_confirmation_template'))
            template_id = self.env['mail.template'].search([('id', '=', template_id)]).id
            if not template_id:
                template_id = self.env['ir.model.data']._xmlid_to_res_id('sale.mail_template_sale_confirmation', raise_if_not_found=False)
        if not template_id:
            template_id = self.env['ir.model.data']._xmlid_to_res_id('sale.email_template_edi_sale', raise_if_not_found=False)

        return template_id

    def action_quotation_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'project.quotation',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).number,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'quotation_sent')
        return self.pool['report'].get_action(cr, uid, ids, 'contracting_management.quotation_report', context=context)

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id and self.project_id.is_multi_quotation == False:
            quotation = self.env['project.quotation'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if quotation:
                raise UserError( _('You Have Project Quotation For This Project'))


    def set_to_draft(self):
        for rec in self:
            rec.status='draft'
    def confirm_quotation(self):
        for rec in self:
            rec.status='confirmed'

    def create_bid_requirment(self):
        for rec in self:
            for bid in rec.bid_requirement_ids:
                bid.unlink()
            tax_ids = self.env['account.tax'].search([('is_default','=',True),('type_tax_use','=','sale')])
            project=self.env['project.project'].search([('id','=',rec.project_id.id)])
            for line in project.bid_requirement_ids:
                print('line.cost_amount,',line.cost_amount)
                self.env['quotation.bid.requirement'].create({
                    'quotation_id':self.id,
                    'wcateg_id':line.wcateg_id.id,
                    'product_id':line.product_id.id,
                    'description':line.description,
                    'qty':line.qty,
                    'uom_id':line.uom_id.id,
                    'unit_cost':line.unit_cost,
                    'cost_amount':line.cost_amount,
                    'margin':line.margin,
                    'invoice_line_tax_id': [(6, 0, tax_ids.ids)],
                    'sales_price':line.sales_price,
                    'sales_amount':line.sales_amount,
                })

    @api.depends('bid_requirement_ids.amount_tax', )
    def _compute_tax(self):
        for rec in self:
            rec.amount_tax = sum(x.amount_tax for x in rec.bid_requirement_ids)
            # rec.amount_tax = 0.0
    @api.depends('bid_requirement_ids.sales_amount',)
    def _compute_amount(self):
        self.amount_untaxed = sum(line.sales_amount for line in self.bid_requirement_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('project.quotation')
        vals['number'] = sequence or '/'
        return super(ProjectQuotation, self).create(vals)

class QuotationBid(models.Model):
    _name = 'quotation.bid.requirement'

    quotation_id = fields.Many2one(comodel_name="project.quotation", string="Project", )
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    description = fields.Char(related='product_id.name', string='Description')
    qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    unit_cost = fields.Float('Unit Cost',)
    cost_amount = fields.Float('Cost Amount', compute='_Compute_cost_amount')
    margin = fields.Float('Margin %', )
    sales_price = fields.Float('Sales Price', compute='_Compute_sales_amount')
    sales_amount = fields.Float('Amount', compute='_Compute_sales_amount')
    invoice_line_tax_id = fields.Many2many('account.tax', string='Taxes')
    amount_tax = fields.Float('Amount',compute='_compute_amount_tax')

    @api.depends('invoice_line_tax_id', 'sales_amount')
    def _compute_amount_tax(self):
        for rec in self:
            rec. amount_tax = 0.0
            amount_tax = 0.0
            for line in rec.invoice_line_tax_id:
                amount_tax += (rec.sales_amount * line.amount/100)
                rec.amount_tax = amount_tax

    @api.depends('sales_price', 'margin', 'qty')
    def _Compute_sales_amount(self):
        for rec in self:
            rec.sales_price = rec.unit_cost + (rec.unit_cost * (rec.margin) / 100)
            rec.sales_amount = rec.sales_price * rec.qty

    @api.depends('unit_cost', 'qty')
    def _Compute_cost_amount(self):
        for rec in self:
            rec.cost_amount = rec.unit_cost * rec.qty
