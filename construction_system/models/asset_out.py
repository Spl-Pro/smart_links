# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class DownPayment(models.Model):
    _name = 'asset.move.out'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Move No", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             default='draft')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    date = fields.Date('Date',default=datetime.today())
    asset_id = fields.Many2one('account.asset', string="Asset", )
    reason = fields.Char('Reason')
    depreciation_end_date=fields.Date('Last Depreciation Calc Date')
    depreciation_closed=fields.Boolean('Depreciation Closed')
    note = fields.Text('Description')

    # @api.multi
    def confirm_asset(self):
        for rec in self:
            project_assets_id = self.env['project.assets'].search([('asset_id', '=', rec.asset_id.id),
                                                                   ('project_id', '=', rec.project_id.id),
                                                                   ('state', '=', 'in_project'),
                                                                   ])
            project_assets_id.end_date = rec.date
            project_assets_id.state = 'out_project'
            rec.asset_id.project_id = False
            rec.state = 'confirmed'

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('asset.move.out')
        vals['number'] = sequence or '/'
        return super(DownPayment, self).create(vals)
