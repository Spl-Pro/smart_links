# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class LcAccounting(models.Model):
    _name = 'project.works.category'
    _rec_name="name"
    parent_id = fields.Many2one(comodel_name="project.works.category", string="Parent Category", required=False, )
    name=fields.Char('Category ID')
    desc=fields.Char('Category Description')
    note=fields.Text('Notes')