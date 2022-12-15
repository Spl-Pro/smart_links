# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime
class ProjectContract(models.Model):
    _name='project.contract'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Contract No", readonly=True)
    project_id = fields.Many2one('project.project', string="Project", domain=[('awarded', '=', True)])
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                              default='draft')
    date = fields.Date('Date',default=datetime.today())
    partner_id = fields.Many2one(related='project_id.partner_id' , string="Customer", domain=[('customer', '=', True)])
    customer_type = fields.Selection(string="",related='project_id.customer_type',)
    retention_per = fields.Float('Retention %')
    down_payment_per = fields.Float('Down Payment %')
    final_gurantee = fields.Float('Final Gurantee %')

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            contract = self.env['project.contract'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if contract:
                raise UserError (_('This Project Has another Contract'))

    def set_to_draft(self):
        for rec in self:
            rec.status = 'draft'
    def confirm_quotation(self):
        for rec in self:
            rec.status = 'confirmed'
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('project.contract')
        vals['number'] = sequence or '/'
        return super(ProjectContract, self).create(vals)