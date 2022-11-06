from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class Purchase(models.Model):
    _inherit = 'purchase.order'

    is_purchase_req = fields.Boolean(default=False)
    is_reject = fields.Boolean(default=False)
    is_approved = fields.Boolean(default=False)

    def show_approval(self):
        approvals = self.env['approval.approval'].sudo().search([])
        action = self.env.ref('all_in_one_approval_app.action_approval_review').read()[0]
        if len(approvals) > 1:
            action['domain'] = [('id', 'in', approvals.ids)]
        elif len(approvals) == 1:
            action['views'] = [(self.env.ref('all_in_one_approval_app.approval_form').id, 'form')]
            action['res_id'] = approvals.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def button_confirm(self):
       approval_type = self.env['approval.type'].sudo().search([('model_id.name','=',self._description),('model_id.model','=',self._name)], limit=1)
       res = super(Purchase, self).button_confirm()
       if self.env.user.has_group('all_in_one_approval_app.group_approval_user') or self.env.user.has_group('all_in_one_approval_app.group_approval_manager'):
         if approval_type and approval_type.approve_amount > 0 and approval_type.approve_amount < self.amount_total:
              if self.state != 'to approve' and self.is_purchase_req != True:
                self.write({'state': 'to approve', 'is_purchase_req':True})
       else:
         return res

    def purchase_approval(self):
       view_id = self.env.ref('all_in_one_approval_app.approve_request_wizard')
       ctx = self._context.copy()
       approval_type = self.env['approval.type'].sudo().search([('model_id.name','=',self._description),('model_id.model','=',self._name)], limit=1)
       if view_id:
            approval_data = {
                'name' : _('Purchase Approval Confirmation'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'approve.request',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'title' :"Purchase Request for - " +str(self.name),
                            'origin' : self.name,
                            'type_id':approval_type.id,
                            'origin_po_id':self.id,
                            'to':self.partner_id.email,
                             },
            }

       return approval_data
