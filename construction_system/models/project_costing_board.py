# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ProjectCostingBoard(models.Model):
    _name='project.costing.board'
    name=fields.Char('Name')