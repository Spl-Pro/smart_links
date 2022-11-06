# -*- coding: utf-8 -*-

from odoo import api, fields, models,_

class ApproveRequest(models.TransientModel):
    _name = "approve.request"
    _description = "Approve Request"

    origin_id = fields.Many2one('sale.order', string="Origin ")
    origin_po_id = fields.Many2one('purchase.order', string="Origin ")
    title = fields.Char("Request Name")
    reference = fields.Char()
    details = fields.Text()
    origin = fields.Char()
    req_date = fields.Datetime('Date', default=lambda *a: fields.Datetime.now(),)
    type_id = fields.Many2one('approval.type')
    res_model_id = fields.Many2one('ir.model', 'Document Model', ondelete='cascade')

    @api.model
    def default_get(self,default_fields):
        res = super(ApproveRequest, self).default_get(default_fields)
        ctx = self._context
        data = {
            'origin_po_id':ctx.get('origin_po_id'),
            'origin_id':ctx.get('origin_id'),
            'title':ctx.get('title'),
            'origin':ctx.get('origin'),
            'type_id':ctx.get('type_id'),
            'details':"Please review my request approval"
        }
        res.update(data)
        return res

    def _compute_resource_ref(self):
        active_id=self.env.context.get('active_id')
        sale = self.env['sale.order'].browse(active_id)
        for rating in sale:
            if rating.res_model and rating.res_model in self.env:
                rating.resource_ref = '%s,%s' % (rating.res_model, rating.res_id or 0)
            else:
                rating.resource_ref = None

    @api.model
    def _selection_target_model(self):
        active_id=self.env.context.get('active_id')
        sale = self.env['sale.order'].browse(active_id)
        return [(model.model, model.name) for model in self.env['ir.model'].search([])]

    @api.model
    def _default_ref_so(self):
        active_id=self.env.context.get('active_id')
        sale = self.env['sale.order'].browse(active_id)
        return sale

    def confirm_approval(self):
        approver_user = False
        approver_list = []
        sale = self.env['approval.type'].sudo().search([('model_id.model','=','sale.order')], limit=1)
        purchase = self.env['approval.type'].sudo().search([('model_id.model','=','purchase.order')], limit=1)
        if self.type_id.approver_ids:
            for approver in self.type_id.approver_ids:
                approver_user = approver.user_id.id
                approver_list.append(approver.id)
        req_approval = self.env['approval.approval'].create({'name':self.title,
            'request_by_id':self.env.user.id, 
            'state':'submit',
            'type_id':self.type_id.id,
            'approver_id':approver_user,
            'date':self.req_date,
            'approver_ids':[(6,0,approver_list)],
            'log':"Submitted " +(self.title),
            })
        if self.origin_id:
            self.origin_id.write({'is_sale_req':True})
            req_approval.write({'origin_id':self.origin_id.id, 'is_origin_so':True,'source':self.origin_id.name})
            source = self.origin_id.name
        
        if self.origin_po_id:
            self.origin_po_id.write({'is_purchase_req':True})
            req_approval.write({'origin_po_id':self.origin_po_id.id, 'is_origin_po':True,'source':self.origin_po_id.name})
            source = self.origin_po_id.name

        views_id=[(self.env.ref('all_in_one_approval_app.approval_form').id, 'form')]
        template_id = self.env.ref('all_in_one_approval_app.submit_request_template')
        if template_id:
            values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_to'] = self.env.context.get('to') or ''
            values['author_id'] = self.env.user.partner_id.id
            values['subject'] = "Submit Request Approval"
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                msg_id.sudo().send()

        return {
            'name': 'Request Approvals',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_id':req_approval.id,
            'views': views_id,
            'res_model': 'approval.approval',
            'domain': [('source','=',source)],
        }


# ------- change approver -----------
class ChangeApprover(models.TransientModel):
    _name = 'change.approver'
    _description = 'Change Approver'

    log = fields.Char("Description", required=True)
    new_approver_id = fields.Many2one('res.users', required=True)

    def confirm(self):
        active_id = self.env.context.get('active_id')
        approval = self.env['approval.approval'].browse(active_id)
        approval.write({'log':self.log, 'approver_id':self.new_approver_id.id})
        for appr in approval.approver_ids:
            appr.write({'user_id':self.new_approver_id.id})
        template_id = self.env.ref('all_in_one_approval_app.change_approver_template')
        if template_id:
            values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_to'] = self.new_approver_id.email or ''
            values['author_id'] = self.env.user.partner_id.id
            values['subject'] = "Changed Request Approver"
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                msg_id.sudo().send()
        return approval


# ----------  Reject ----------
class RequestReject(models.TransientModel):
    _name = 'request.reject'
    _description = 'Request Reject'

    log = fields.Char("Description", required=True)

    def confirm(self):
        approval = self.env['approval.approval'].browse(self.env.context.get('active_id'))
        sale = self.env['sale.order'].search([('name','=',approval.source)])
        approval.write({'log':self.log,'state':'reject','is_reject':True})
        sale.write({'is_reject':True})        
        if approval.origin_po_id:
            approval.origin_po_id.write({'is_reject':True})
        if approval.origin_id:
            approval.origin_id.write({'is_reject':True})
        for approver in approval.approver_ids:
            if approver.user_id == self.env.user:
                approver.write({'status':'reject'})
        template_id = self.env.ref('all_in_one_approval_app.reject_request_template')
        if template_id:
            values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_to'] = self.env.user.partner_id.email or ''
            values['author_id'] = self.env.user.partner_id.id
            values['subject'] = "Approval Request Rejected"
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                msg_id.sudo().send()
        return True


class RequestRework(models.TransientModel):
    _name = 'request.rework'
    _description = 'Request Rework'

    origin_id = fields.Many2one('sale.order', "Origin ")
    origin_po_id= fields.Many2one('purchase.order', "Origin ")
    type_id = fields.Many2one('approval.type')
    name =  fields.Char()
    origin = fields.Char()

    @api.model
    def default_get(self, default_fields):
        res = super(RequestRework, self).default_get(default_fields)
        ctx = self._context
        data = {'type_id':ctx.get('type_id'),'origin':ctx.get('origin'), 'origin_po_id':ctx.get('origin_po_id')}
        res.update(data)
        return res

    def confirm(self):
        approval = self.env['approval.approval'].sudo().search([('source','=',self.origin)], limit=1)
        sale = self.env['sale.order'].search([('name','=',self.origin)], limit=1)
        sale.write({'is_rework':True, 'is_approval':True})
        approval.write({'log':'Request in Rework', 'state':'draft'})
        for approver in approval.approver_ids:
            if approver.user_id == self.env.user:
                approver.write({'status':'Request in Rework'})
        template_id = self.env.ref('all_in_one_approval_app.rework_request_template')
        if template_id:
            values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_to'] = self.env.context.get('to') or ''
            values['author_id'] = self.env.user.partner_id.id
            values['subject'] = "Approval Request in Rework"
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                msg_id.sudo().send()
        return True
