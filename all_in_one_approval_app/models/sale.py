
from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class Sale(models.Model):
    _inherit = 'sale.order'

    is_sale_req = fields.Boolean(default=False)
    req_done = fields.Boolean()
    is_request = fields.Boolean()
    is_rework = fields.Boolean()
    is_reject = fields.Boolean()
    is_approval = fields.Boolean()

    def action_confirm(self):
       approval_type = self.env['approval.type'].sudo().search([('model_id.name','=',self._description),('model_id.model','=',self._name)], limit=1)       
       res = super(Sale, self).action_confirm()
       if approval_type and approval_type.approve_amount > 0 and approval_type.approve_amount < self.amount_total and self.is_sale_req == False:
           raise ValidationError(_('Approval must be required...!'))
       if self.is_approval:
          return res    

    def request_rework(self):
       view_id = self.env.ref('all_in_one_approval_app.approve_request_sale_wizard1')
       active_id = self.env.context.get('active_id')
       ctx = self._context.copy()
       approval_type = self.env['approval.type'].sudo().search([('model_id.name','=',self._description),('model_id.model','=',self._name)], limit=1)
       if view_id:
            approval_data = {
                'name' : _('Request Rework Confirmation'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'request.rework',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'origin':self.name,
                            'type_id':approval_type.id,
                            'to':self.partner_id.email,
                             },
            }
       self.is_rework = True
       return approval_data

    def sale_approval(self):
       view_id = self.env.ref('all_in_one_approval_app.approve_request_sale_wizard')
       ctx = self._context.copy()       
       approval_type = self.env['approval.type'].sudo().search([('model_id.name','=',self._description),('model_id.model','=',self._name)], limit=1)
       if approval_type and approval_type.approve_amount <=0:
          raise ValidationError(_("Please configure valid approve amount in approval type..!"))
       if approval_type and approval_type.approve_amount > self.amount_total:
          raise ValidationError(_("Sale order amount must be greater or equal than %d ..!",approval_type.approve_amount))
       if view_id:
            approval_data = {
                'name' : _('Sale Approval Confirmation'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'approve.request',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'origin_id':self.id,
                            'title' :"Sale Request for : " +str(self.name),
                            'origin' : self.name,
                            'type_id':approval_type.id,
                            'from':self.user_id.partner_id.email,
                            'to':self.partner_id.email,
                             },
            }
       return approval_data
