from odoo import models, fields, api,_
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from odoo.exceptions import ValidationError
import base64
from odoo.modules.module import get_module_resource


class ApproverDetails(models.Model):
    _name = 'approver.detail'
    _description = "Approver Details"

    approver_id = fields.Many2one('approval.approval',string="Approval ")
    type_id = fields.Many2one('approval.type',string="Approval Type")
    user_id = fields.Many2one('res.users')
    user_role = fields.Char('User Role')
    group_id = fields.Many2one('res.groups', string="Deputy Group Access")
    other_user_id = fields.Many2one('res.users', string="Other(Special) User")
    approval_type = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Approval Type ')
    status  = fields.Char()
    approve_check = fields.Boolean('Approve Check', default=False, copy=False)


class ApprovalType(models.Model):
    _name = 'approval.type'
    _description = "Approval Type"

    name = fields.Char()
    approval_type = fields.Boolean("Approval for Existing Model")
    approver_ids = fields.One2many('approver.detail','type_id')
    document = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Document')
    contact = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Contact')
    date = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Date')
    period = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Period')
    item = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Item')
    multi_item = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Multi Item')
    quantity = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Quantity')
    amount = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Amount')
    payment = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Payment')
    reference = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Reference')
    location = fields.Selection([('required', 'Required'), ('optional', 'Optional'),('none', 'None')],string = 'Location')
    company_id = fields.Many2one('res.company')
    group_id = fields.Many2one('res.groups')
    description = fields.Char()
    help_note = fields.Char()
    number_of_approver = fields.Integer()
    model_id = fields.Many2one('ir.model')
    domain = fields.Char("Domain Description")
    num_of_review = fields.Integer("Number of Review", compute='number_of_review')
    is_confirm = fields.Boolean()
    approve_amount = fields.Float("Approval Amount")
    image_1920 = fields.Image()

    def confirm(self):
        if not self.approver_ids:
            raise ValidationError(_("Please configure approvers details...!"))
        self.is_confirm = True

    @api.onchange('approver_ids')
    def check_approver(self):
        if self.approver_ids:
            self.number_of_approver = len(self.approver_ids)

    def new_request(self):
        ctx = self._context.copy()
        ctx['default_journal_id'] = self.id
        ctx.update({'is_submit':True,'type_id' : self.id,'request_by_id':self.env.user.id,'approval_list':self.approver_ids.ids})
        return {
            'name': _('Approval Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'approval.approval',
            'view_id': self.env.ref('all_in_one_approval_app.approval_form').id,
            'context': ctx,
        }

    def review(self):
        approvals = self.env['approval.approval'].search([('state','=','submit'),('type_id','=',self.id)])
        action = self.env.ref('all_in_one_approval_app.action_approval_review').read()[0]
        if len(approvals) > 1:
            action['domain'] = [('id', 'in', approvals.ids)]
        elif len(approvals) == 1:
            action['views'] = [(self.env.ref('all_in_one_approval_app.approval_form').id, 'form')]
            action['res_id'] = approvals.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.model
    def number_of_review(self):
        for rec in self:
            approvals = self.env['approval.approval'].search([('state','=','submit'),('type_id','=',rec.id)])
            rec.num_of_review = len(approvals)
