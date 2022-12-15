# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class DownPayment(models.Model):
    _name = 'asset.move.in'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Move No", readonly=True)
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             default='draft')
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    responsible=fields.Many2one('hr.employee',string='Responsible')
    date = fields.Date('Date',default=datetime.today())
    asset_id = fields.Many2one('account.asset', string="Asset", )
    reason = fields.Char('Reason')
    depreciation_start_date=fields.Date('Depreciation Start Date')
    depreciation_end_date=fields.Date('Last Depreciation Calc Date')
    note = fields.Text('Description')

    @api.constrains('project_id')
    def _project_id_assets(self):
        if self.project_id:
            project = self.env['project.project'].search([])
            for pro in project:
                if self.asset_id.project_id.id==pro.id:
                    raise UserError(_('This Asset In the project: %s')
                                     % (self.asset_id.project_id.name))

    # @api.multi
    def confirm_asset(self):
        for rec in self:
            asset=self.env['account.asset'].search([('id','=',rec.asset_id.id)])
            asset.project_id=rec.project_id
            self.env['project.assets'].create({
                'project_id':rec.project_id.id,
                'asset_id':rec.asset_id.id,
                'state':'in_project',
                'start_date':rec.date,
            })
            rec.state = 'confirmed'


    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('asset.move.out')
        vals['number'] = sequence or '/'
        return super(DownPayment, self).create(vals)


class AssetAccount(models.Model):
    _inherit='account.asset'
    project_id=fields.Many2one('project.project', string="Project",)