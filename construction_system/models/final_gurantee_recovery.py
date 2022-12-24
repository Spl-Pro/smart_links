# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class FinalGurantee(models.Model):
    _name='final.gurantee.recovery'
    name=fields.Char('Name')