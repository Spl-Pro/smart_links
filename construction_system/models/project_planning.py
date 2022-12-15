# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime

class ProjectPlanning(models.Model):
    _name = 'project.planning'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Planning Number", readonly=True)
    description = fields.Char('Description')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer", domain=[('customer', '=', True)])
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account')
    user_id = fields.Many2one('res.users', string='Created By', )
    # default=lambda self: self.env.uid)
    start_date = fields.Date('Start Date',default=datetime.today())
    notes = fields.Text('Notes')
    retention_per = fields.Float('Retention %')
    down_payment_per = fields.Float('Down Payment %')

    total_material = fields.Float('Total Material Cost:', compute='compute_total_material', store=True)
    total_labor = fields.Float('Total Labor Cost:', compute='compute_total_labor', store=True)
    total_overhead = fields.Float('Total Overhead Cost:', compute='compute_total_overhead', store=True)
    total_cost = fields.Float('Total Cost:', compute='compute_total_cost', store=True)

    task_material_ids = fields.One2many(comodel_name="task.material", inverse_name="task_id", string="Task Material",
                                        required=False, )
    task_labor_ids = fields.One2many(comodel_name="task.labor", inverse_name="task_id", string="Task Material",
                                     required=False, )
    task_overhead_ids = fields.One2many(comodel_name="task.overhead", inverse_name="task_id", string="Task Material",
                                        required=False, )
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('to_approve', 'Approved'), ],
                             default='draft')

    is_down_payment = fields.Boolean('Is Down')
    is_project_invoice = fields.Boolean('Is Down')
    invoice_id = fields.Many2one('account.move', string="Down Payment Invoice")
    analytic_account_id = fields.Many2one(related='project_id.analytic_account_id', string="Analytic Account")

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            planning = self.env['project.planning'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            quotation = self.env['project.quotation'].search(
                [('partner_id', '=', self.partner_id.id), ('project_id', '=', self.project_id.id)])
            if planning:
                raise UserError(_('You Have Project Planning For This Project'))
            if self.project_id.awarded!=True:
                raise UserError( _('The Project Not Awarded'))

    def create_bid_requirment(self):
        for rec in self:
            for bid in rec.task_material_ids:
                bid.unlink()
            project = self.env['project.quotation'].search([('project_id', '=', rec.project_id.id)])
            for line in project.bid_requirement_ids:
                self.env['task.material'].create({
                    'task_id': self.id,
                    'wcateg_id': line.wcateg_id.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'qty': line.qty,
                    'uom_id': line.uom_id.id,
                    'unit_cost': line.unit_cost,
                    # 'cost_amount': line.cost_amount,
                    # 'margin': line.margin,
                    # 'sales_price': line.sales_price,
                    # 'sales_amount': line.sales_amount,
                })

    def approve(self):
        for rec in self:
            rec.project_id.total_cost = rec.total_cost
            rec.state = 'to_approve'

    def down_payment(self):
        for rec in self:
            if rec.project_id.down_payment_account:
                account_id = self.env['account.move'].create({
                    'partner_id': rec.partner_id.id,
                    'project_id': rec.project_id.id,
                    'account_id': rec.partner_id.property_account_receivable.id,
                    'planning_id': rec.id,
                    'data_invoice': rec.start_date,
                    'type': 'out_invoice',
                })
                self.env['account.move.line'].create({
                    'invoice_id': account_id.id,
                    'name': 'Down Payment',
                    'quantity': 1,
                    'account_id': rec.project_id.down_payment_account.id,
                    'price_unit': rec.total_cost * rec.down_payment_per / 100
                })
            else:
                raise UserError( _('You Must Choose Project Down Payment Account'))
            rec.invoice_id = account_id.id
            rec.is_down_payment = True

    def create_planning_invoices(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'account invoice',
                'view_type': 'form',
                'view_id': self.env.ref('account.invoice_form').id,
                'domain': [('type', '=', 'out_invoice')],
                'res_id': False,
                'view_mode': 'form',
                'res_model': 'account.move',
                'context': {'default_partner_id': rec.partner_id.id,
                            'default_planning_id': rec.id,
                            'default_project_id': rec.project_id.id,
                            'default_account_id': rec.project_id.down_payment_account.id,
                            'default_data_invoice': rec.start_date,
                            'default_is_project_invoice': True, },
                'target': 'current',
            }

    def view_down_payment(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'account invoice',
                'view_type': 'form',
                'view_id': self.env.ref('account.invoice_form').id,
                'domain': [('type', '=', 'out_invoice')],
                'res_id': rec.invoice_id.id,
                'view_mode': 'form',
                'res_model': 'account.move',
                'target': 'current',
            }

    @api.depends('task_material_ids.amount')
    def compute_total_material(self):
        for rec in self:
            rec.total_material = sum(line.qty * line.unit_cost for line in rec.task_material_ids)

    @api.depends('task_labor_ids.amount')
    def compute_total_labor(self):
        for rec in self:
            rec.total_labor = sum(line.hours * line.hour_rate for line in rec.task_labor_ids)

    @api.depends('task_overhead_ids.cost')
    def compute_total_overhead(self):
        for rec in self:
            rec.total_overhead = sum(line.cost for line in rec.task_overhead_ids)

    @api.depends('total_material', 'total_labor', 'total_overhead')
    def compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.total_material + rec.total_labor + rec.total_overhead
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('project.planning')
        vals['number'] = sequence or '/'
        return super(ProjectPlanning, self).create(vals)


class MaterialTask(models.Model):
    _name = 'task.material'
    task_id = fields.Many2one(comodel_name="project.planning", string="Project task", )
    subcontracted = fields.Boolean('Subcontracted')
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product ')
    description = fields.Char(related='product_id.name', string='Description')
    qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    unit_cost = fields.Float('Sales Unit Cost')
    amount = fields.Float('Amount', compute='_Compute_amount')

    @api.depends('unit_cost', 'qty')
    def _Compute_amount(self):
        for rec in self:
            rec.amount = rec.qty * rec.unit_cost


class laborTask(models.Model):
    _name = 'task.labor'
    task_id = fields.Many2one(comodel_name="project.planning", string="Project_task", )
    product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'service')])
    description = fields.Char(related='product_id.name', string='Description')
    hours = fields.Float('Hours')
    hour_rate = fields.Float('Hour Rate')
    amount = fields.Float('Amount', compute='_Compute_amount')

    @api.depends('hour_rate', 'hours')
    def _Compute_amount(self):
        for rec in self:
            rec.amount = rec.hours * rec.hour_rate


class overheadTask(models.Model):
    _name = 'task.overhead'
    task_id = fields.Many2one(comodel_name="project.planning", string="Project_task", )
    journal_id = fields.Many2one('account.move', string='Journal', )
    description = fields.Many2one(related='journal_id.journal_id', string='Description')
    cost = fields.Float('Cost', )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for rec in self:
            if rec.journal_id:
                rec.cost = rec.journal_id.line_id[0].debit if rec.journal_id.line_id[0].debit > 0 else \
                    rec.journal_id.line_id[0].credit





class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    qty_befor_payment = fields.Float('Quantity',default=1, )
    total_befor_payment = fields.Float('Amount', compute="compute_total_befor_payment")

    @api.depends('product_id','price_unit','qty_befor_payment')
    def compute_total_befor_payment(self):
        for rec in self:
            rec.quantity = (1-((rec.invoice_id.planning_id.down_payment_per / 100) + (
                     rec.invoice_id.planning_id.retention_per / 100)))
            rec.total_befor_payment= rec.qty_befor_payment* rec.price_unit

    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            if rec.move_id.project_id:
                if  rec.invoice_id.type=='out_invoice':
                    rec.account_id = rec.invoice_id.project_id.income_account
                    if rec.invoice_id.type == 'in_invoice':
                        rec.account_id =self.project_id.sub_contract_down_payment_account


class AccountMove(models.Model):
    _inherit = 'account.move'
    project_id = fields.Many2one(comodel_name="project.project", string="Project ",)
    preliminary_gurantee_id = fields.Many2one(comodel_name="preliminary.gurantee", string="Preliminary Gurantee ",)
    sale_id = fields.Many2one(comodel_name="sale.order", string="Sale Order ",)

