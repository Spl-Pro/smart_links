from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class Approvals(models.Model):
	_name = 'approval.approval'
	_description = "Approvals"

	is_approve_check = fields.Boolean('Check Approved')
	is_reject = fields.Boolean()
	is_cancel = fields.Boolean()
	is_change_approver = fields.Boolean()
	is_submit = fields.Boolean()
	is_origin_so = fields.Boolean()
	is_origin_po = fields.Boolean()    
	type_id = fields.Many2one('approval.type',string="Approval Type")
	name = fields.Char()
	description = fields.Char("Details")
	image = fields.Many2many('ir.attachment', string="Image")
	state = fields.Selection([('draft', 'Draft'), ('submit', 'Submitted'),('approved', 'Approved'),('cancel', 'Cancelled'),('reject', 'Rejected')],string = "Status", default='draft')
	approver_id = fields.Many2one('res.users')
	type_id = fields.Many2one('approval.type')
	payment = fields.Float('Payment')
	request_by_id = fields.Many2one('res.users')
	source = fields.Char()
	log = fields.Char("Log Details")
	start_date = fields.Datetime("Start Date")
	expire_date = fields.Datetime()
	approver_ids = fields.One2many('approver.detail','approver_id', string="Approver List")
	origin_id= fields.Many2one('sale.order', string="Origin", readonly=True)
	origin_po_id= fields.Many2one('purchase.order',string=" Origin ", readonly=True)
	is_payment = fields.Boolean()
	is_date = fields.Boolean()
	is_contact = fields.Boolean()
	is_item = fields.Boolean()
	is_multi_item = fields.Boolean()
	is_document = fields.Boolean()
	is_reference = fields.Boolean()
	is_payment = fields.Boolean()
	is_amount = fields.Boolean()
	is_quantity = fields.Boolean()
	is_location = fields.Boolean()
	is_period= fields.Boolean()
	document = fields.Binary()
	contact = fields.Many2one('res.partner')
	date =  fields.Date()
	period = fields.Datetime()
	item = fields.Many2one('product.product')
	multi_item = fields.Many2many('product.product')
	quantity = fields.Float()
	amount = fields.Float()
	payment = fields.Float()
	reference = fields.Char()
	location = fields.Char()
	is_new_model = fields.Boolean()


	def read(self, fields, load='_classic_read'):
		if self.approver_ids:
			for line in self.approver_ids.filtered(lambda x :x.user_id == self.env.user):
				if not line.approve_check:
					self.is_approve_check = False
		return super(Approvals, self).read(fields, load=load)

	@api.model
	def default_get(self, default_fields):
		res=super(Approvals, self).default_get(default_fields)
		ctx = self.env.context
		data = {'is_submit':ctx.get('is_submit'),'type_id':ctx.get('type_id'),'request_by_id':ctx.get('request_by_id'), 'approver_ids':[(6,0,ctx.get('approval_list'))]}
		approval_type = self.env['approval.type'].browse(ctx.get('type_id')) 
		res.update(data)
		if approval_type.approval_type == False:
			
			res.update({'is_new_model':True})
			if approval_type.payment == 'required':
				res.update({'is_payment':True})
			if approval_type.date == 'required':
				res.update({'is_date':True})
			if approval_type.contact == 'required':
				res.update({'is_contact':True})

			if approval_type.item == 'required':
				res.update({'is_item':True})

			if approval_type.multi_item == 'required':
				res.update({'is_multi_item':True})

			if approval_type.document == 'required':
				res.update({'is_document':True})

			if approval_type.reference == 'required':
				res.update({'is_reference':True})

			if approval_type.amount == 'required':
				res.update({'is_amount':True})

			if approval_type.quantity == 'required':
				res.update({'is_quantity':True})

			if approval_type.location == 'required':
				res.update({'is_location':True})
		return res

	def cancel_request(self):
		self.state = 'cancel'
		template_id = self.env.ref('all_in_one_approval_app.cancel_request_template')
		if template_id:
			values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
			values['email_to'] = self.request_by_id.email or ''
			values['author_id'] = self.env.user.partner_id.id
			values['subject'] = "Cancelled Request"
			mail_mail_obj = self.env['mail.mail']
			msg_id = mail_mail_obj.sudo().create(values)
			if msg_id:
				msg_id.sudo().send()

	@api.depends('type_id.approver_ids')
	def get_approve_btn(self):
		for rec in self:
			rec.is_approve = False
			for approver in rec.type_id.approver_ids:
				if approver.user_id == rec.env.user:
					rec.is_approve = True

	def req_submit(self):
		if not self.type_id.approver_ids:
			raise ValidationError(_('Please define approvers in approver types...!'))
		self.state = 'submit'
		for approver in self.type_id.approver_ids:
			self.approver_id = approver.user_id.id
			self.write({'request_by_id':self.env.user.id})
		template_id = self.env.ref('all_in_one_approval_app.submit_req_template2')
		if template_id:
			values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
			values['email_to'] = self.request_by_id.email or ''
			values['author_id'] = self.env.user.partner_id.id
			values['subject'] = " Submit Approval Request"
			mail_mail_obj = self.env['mail.mail']
			msg_id = mail_mail_obj.sudo().create(values)
			if msg_id:
				msg_id.sudo().send()

	def req_approve(self):
		po=self.env['purchase.order'].search([('name','=',self.source)], limit=1)
		so=self.env['sale.order'].search([('name','=',self.source)], limit=1)
		user_list = []
		if self.approver_ids:
			for line in self.approver_ids:
				if self.env.user == line.user_id:
					line.approve_check = True
				user_list.append(line.user_id.id)
		if self.env.user.id not in user_list:
			raise ValidationError(_("Login user (%s) can not approved this Request...! ",self.env.user.name))
		# Sale Order Approval Process
		if so:
			is_full_approved = all(line.approve_check==True for line in self.approver_ids)
			if is_full_approved:
				so.write({'is_approval':True})
				so.action_confirm()
				template_id = self.env.ref('all_in_one_approval_app.request_mail_template')
				if template_id:
					values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
					values['email_to'] = self.request_by_id.email or ''
					values['author_id'] = self.env.user.partner_id.id
					values['subject'] = " Approved Request Notification"
					mail_mail_obj = self.env['mail.mail']
					msg_id = mail_mail_obj.sudo().create(values)
					if msg_id:
						msg_id.sudo().send()
		self.log = "approved this request"
		self.is_approve_check = True
		# Purchase Order Approval Process
		if po:
			is_full_approved = all(line.approve_check==True for line in self.approver_ids)
			if is_full_approved:
				po.button_confirm()
				po.write({'is_approved':True})
				po.button_approve()
				self.state = 'approved'

				template_id = self.env.ref('all_in_one_approval_app.request_mail_template')
				if template_id:
					values = template_id.sudo().generate_email(self.id,['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
					values['email_to'] = self.request_by_id.email or ''
					values['author_id'] = self.env.user.partner_id.id
					values['subject'] = " Approved Request Notification"
					mail_mail_obj = self.env['mail.mail']
					msg_id = mail_mail_obj.sudo().create(values)
					if msg_id:
						msg_id.sudo().send()

	def reject_request(self):
		self.origin.is_request=True
		return {
			'name': 'Reject Request',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_id':self.id,
			'views': [(self.env.ref('all_in_one_approval_app.request_reject_wizard').id, 'form')],
			'res_model': 'request.rework',
		}
