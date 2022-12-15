# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime, timedelta


class Project(models.Model):
    _inherit = 'project.project'

    is_planning = fields.Boolean('Project Planning')
    project_type = fields.Selection(string="Project Types", selection=[('internal_project', 'Internal Project'),
                                                                       ('customer_project', 'Customer Project'), ],
                                    required=False, )
    project_sub_type = fields.Selection(string="Project Sub Type", selection=[('time_material', 'Time & Material'),
                                                                              ('fixed_price', 'Fixed Price'), ],
                                        required=False, )
    project_contract_id = fields.Many2one(comodel_name="project.contract",
                                          string="Project Contract", )
    customer_type = fields.Selection(string="", selection=[('public_sector', 'Public Sector'),
                                                           ('private_sector', 'Private Sector'), ], required=False, )
    bid_requirement_ids = fields.One2many(comodel_name="bid.requirement", inverse_name="project_id",
                                          string="Bid Requirments", )
    asset_ids = fields.One2many(comodel_name="project.assets", inverse_name="project_id",
                                string="Assets", )
    awarded = fields.Boolean('Confirm Quotation',)
    is_multi_quotation = fields.Boolean('Multi Quotation',  )
    location_id = fields.Many2one('stock.location', string='Project Location',)
    preliminary_gurantee_id = fields.Many2one(comodel_name="preliminary.gurantee", string="Preliminary Gurantee",
                                              compute='compute_preliminary_gurantee')
    preliminary_gurantee_recovery_id = fields.Many2one(comodel_name="preliminary.gurantee.recovery", string="Preliminary Gurantee Recovery",
                                              compute='compute_preliminary_gurantee')
    contract_count =fields.Integer('Contracts',compute='compute_count')

    def compute_count(self):
        for record in self:
            record.contract_count = self.env['project.contract'].search_count(
                [('project_id', '=', self.id)])

    def get_contract(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contracts',
            'view_mode': 'tree',
            'res_model': 'project.contract',
            'domain': [('project_id', '=', self.id)],
            'context': "{'create': False}"
        }



    @api.depends('name')
    def compute_preliminary_gurantee(self):
        for rec in self:
            preliminary=self.env['preliminary.gurantee'].search([('project_id','=',self.id)])
            rec.preliminary_gurantee_id = preliminary.id
            preliminary_recovery = self.env['preliminary.gurantee.recovery'].search([('project_id', '=', self.id)])
            rec.preliminary_gurantee_recovery_id = preliminary_recovery.id


    # @api.depends('partner_id')
    # def compute_project_location(self):
    #     for rec in self:
    #         if rec.partner_id:
    #             location = self.env['stock.location'].search(
    #                 [('project_id', '=', self.id), ('usage', '=', 'customer'), ('customer', '=', rec.partner_id.id)])
    #             rec.location_id = location.id

    total_cost = fields.Float('Total Cost:', compute='compute_total_cost')
    retention_account2 = fields.Many2one('account.account', string='Retention Account', compute="compute_accounts")
    retention_account = fields.Many2one('account.account', string='Retention Account', )
    down_payment_account = fields.Many2one('account.account', string='Down Payment Account')
    income_account = fields.Many2one('account.account', string='Income Account')
    preliminary_guarantee = fields.Many2one('account.account', string='Preliminary Guarantee Account')
    bank_commission = fields.Many2one('account.account', string='Bank Commission Account')
    final_guarantee = fields.Many2one('account.account', string='Final Guarantee Account')
    project_material_cost = fields.Many2one('account.account', string='Project Material Cost Account')
    sub_contract_retention_account = fields.Many2one('account.account', string='Sub-Contracting Retention Account',
                                                     config_parameter='base.retention_account')
    sub_contract_down_payment_account = fields.Many2one('account.account',
                                                        string='Sub-Contracting Down Payment Account',
                                                        config_parameter='base.down_payment_account')
    # is_contract = fields.Boolean('Quotation')
    is_quotation = fields.Boolean('Quotation')

    def create_quotation(self):
        sale_order =self.env['project.quotation'].create({
            'project_id':self.id,
        })
        for line in self.bid_requirement_ids:
            sale_order_line =self.env['quotation.bid.requirement'].create({
                'quotation_id':sale_order.id,
                'product_id':line.product_id.id,
                'wcateg_id':line.wcateg_id.id,
                'uom_id':line.uom_id.id,
                'description':line.description,
                'qty':line.qty,
                'cost_amount':line.cost_amount,
                'unit_cost':line.unit_cost,
                'margin':line.margin,
                'sales_price':line.sales_price,
                'sales_amount':line.sales_amount,
            })
            self.is_quotation=True

    @api.depends('bid_requirement_ids.sales_amount')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(l.sales_amount for l in rec.bid_requirement_ids)

    @api.constrains('name')
    def _constrains_name(self):
        analytic_account = self.env['account.analytic.account'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
        })
        self.analytic_account_id =analytic_account.id
    @api.model
    def create(self, vals):

        if self.project_sub_type == 'time_material' and self.awarded == True:
            if self.project_type == 'internal_project':
                self.env['stock.location'].create({
                    'name':self.name,
                    'usage':'internal',
                })
            else:
                self.env['stock.location'].create({
                    'name': self.name,
                    'usage': 'customer',
                })
        return super(Project, self).create(vals)
    def write(self, values):
        for rec in self:
            location =self.env['stock.location'].search([('name','=',rec.name)])
            if location:
                pass
            else:
                if rec.project_type == 'internal_project':
                    self.env['stock.location'].create({
                        'name': rec.name,
                        'usage': 'internal',
                    })
                else:
                    self.env['stock.location'].create({
                        'name': rec.name,
                        'usage': 'customer',
                    })
        return super(Project, self).write(values)
    @api.depends('name')
    def compute_accounts(self):
        config = self.env['project.config.settings.accounts'].search([], limit=1, order='id desc')
        for rec in self:
            rec.retention_account2
            rec.retention_account = config.retention_account
            rec.down_payment_account = config.down_payment_account
            rec.income_account = config.income_account
            rec.preliminary_guarantee = config.preliminary_guarantee
            rec.bank_commission = config.bank_commission
            rec.final_guarantee = config.final_guarantee
            rec.project_material_cost = config.project_material_cost
            rec.sub_contract_retention_account = config.sub_contract_retention_account
            rec.sub_contract_down_payment_account = config.sub_contract_down_payment_account


class LcAccounting(models.Model):
    _name = 'bid.requirement'

    project_id = fields.Many2one(comodel_name="project.project", string="Project", )
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    description = fields.Char( string='Description')
    qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    unit_cost = fields.Float('Unit Cost', )
    cost_amount = fields.Float('Cost Amount', compute='_Compute_cost_amount')
    margin = fields.Float('Margin %', )
    sales_price = fields.Float('Unit Sales Price',compute='_compute_sales_amount' )
    sales_amount = fields.Float('Amount', compute='_compute_sales_amount')


    @api.depends('margin', 'qty')
    def _compute_sales_amount(self):
        for rec in self:
            rec.sales_price = rec.unit_cost + (rec.unit_cost * (rec.margin) / 100)
            rec.sales_amount = rec.sales_price * rec.qty

    @api.depends('unit_cost', 'qty')
    def _Compute_cost_amount(self):
        for rec in self:
            rec.cost_amount = rec.unit_cost * rec.qty


class ProjectAssets(models.Model):
    _name = 'project.assets'

    project_id = fields.Many2one(comodel_name="project.project", string="Project", )
    asset_id = fields.Many2one('account.asset', string="Asset", )
    state = fields.Selection(string="State", selection=[('in_project', 'In Project'), ('out_project', 'Out Project'), ],
                             required=False, )
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    no_days = fields.Float('Number Of Days', compute='compute_no_days')

    @api.depends('start_date', 'end_date')
    def compute_no_days(self):
        for rec in self:
            rec.no_days =0.0
            if rec.start_date and rec.end_date:
                d1 = datetime.strptime(str(rec.end_date), '%Y-%M-%d')
                d2 = datetime.strptime(str(rec.start_date), '%Y-%M-%d')
                delta = d1 - d2
                rec.no_days = delta.days


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_default = fields.Boolean('Default')
    account_collected_id = fields.Many2one('account.account',string='Invoice Tax Account')

    @api.constrains('is_default')
    def constrains_is_default(self):
        if self.is_default:
            tax_sale = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('is_default', '=', True)])
            tax_purchase = self.env['account.tax'].search(
                [('type_tax_use', '=', 'purchase'), ('is_default', '=', True)])

            if len(tax_sale) > 1:
                raise UserError(_('This  Default Sale Tax Must Be Unique'))
            elif len(tax_purchase) > 1:
                raise UserError( _('This Default Tax Purchase Must Be Unique'))
