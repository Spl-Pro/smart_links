# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class projectTask(models.Model):
    _inherit = 'project.task'

    task_type = fields.Selection(string="Task Types", selection=[('material', 'Material'),
                   ('labor', 'Labor'),('overheads', 'Overheads')],)
    task_stage=fields.Many2one('project.task.type',string='Task Stage')
    start_date=fields.Date('Start Date')

    task_material_ids = fields.One2many(comodel_name="task.material", inverse_name="task_id", string="Task Material", required=False, )
    task_labor_ids = fields.One2many(comodel_name="task.labor", inverse_name="task_id", string="Task Material", required=False, )
    task_overhead_ids = fields.One2many(comodel_name="task.overhead", inverse_name="task_id", string="Task Material", required=False, )


class MaterialTask(models.Model):
    _name = 'task.material'
    task_id = fields.Many2one(comodel_name="project.task", string="Project task",)
    product_id=fields.Many2one('product.product',string='Product')
    description=fields.Char(related='product_id.name',string='Description')
    qty=fields.Float('Quantity')
    uom_id=fields.Many2one(related='product_id.uom_id',string='Product')
    unit_cost = fields.Float('Unit Cost')
    amount=fields.Float('Amount',)

    # @api.one
    @api.depends('unit_cost','qty')
    def _Compute_amount(self):
       for rec in self:
           rec.amount=rec.qty * rec.unit_cost


class laborTask(models.Model):
    _name = 'task.labor'
    task_id = fields.Many2one(comodel_name="project.task", string="Project_task",)
    product_id = fields.Many2one('product.product', string='Product', domain=[('type','=','service')])
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
    task_id = fields.Many2one(comodel_name="project.task", string="Project_task",)
    journal_id = fields.Many2one('account.move', string='Journal',)
    description = fields.Many2one(related='journal_id.journal_id', string='Description')
    cost=fields.Float('Cost')

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for rec in self:
            if rec.journal_id:
                rec.cost = rec.journal_id.line_id[0].debit if rec.journal_id.line_id[0].debit > 0 else \
                    rec.journal_id.line_id[0].credit

