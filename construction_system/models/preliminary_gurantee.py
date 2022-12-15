# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class PreliminaryGurantee11(models.Model):
    _name = 'preliminary.gurantee'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    number = fields.Char("Transaction Number", readonly=True)
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                              default='draft')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer')
    bank_account_id = fields.Many2one('account.account', string='Preliminary Gurantee Account',)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_id2 = fields.Many2one('account.move', string='Clear Gurantee Entry')
    date = fields.Date('Date', default=datetime.today())
    preliminary_gurantee_amount = fields.Float('Preliminary Gurantee Amount')
    bank_commission = fields.Float('Bank Commission')
    note = fields.Text('Description')
    is_clear_gurantee = fields.Boolean('is_clear_gurantee')
    awarded = fields.Boolean(related='project_id.awarded')
    journal_count = fields.Integer(compute="_compute_count_all_document", string='Document Count')

    @api.onchange('project_id')
    def onchange_project_id(self):
        setting = self.env['project.config.settings.accounts'].search([])
        self.bank_account_id = setting.preliminary_guarantee
    def _compute_count_all_document(self):
        document = self.env['account.move']
        for record in self:
            record.journal_count = document.search_count([('preliminary_gurantee_id', '=', record.id)])

    # def return_action_to_open_document(self):
    #     action = self.env['ir.actions.act_window'].for_xml_id('account', 'view_move_form')
    #     action['domain'] = [('preliminary_gurantee_id', '=',self.id),]
    #     return action
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('preliminary.gurantee')
        vals['number'] = sequence or '/'
        return super(PreliminaryGurantee11, self).create(vals)

    def clear_gurantee(self):
        for rec in self:
            for rec in self:
                move2 = self.env['account.move'].create({
                    'journal_id': rec.journal_id.id,
                    'date': rec.date,
                    'project_id': rec.project_id.id,
                })
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {
                        'move_id': move2.id,
                        'account_id': rec.bank_account_id.id,
                        'name': rec.project_id.name,
                        'partner_id': rec.partner_id.id,
                        # 'analytic_account_id': rec.project_id.analytic_account_id.id,
                        'debit': rec.preliminary_gurantee_amount,
                        'credit': 0.0,
                    })
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {
                        'move_id': move2.id,
                        'account_id': rec.project_id.preliminary_guarantee.id,
                        # 'analytic_account_id': rec.project_id.analytic_account_id.id,
                        'name': rec.project_id.name,
                        'partner_id': rec.partner_id.id,
                        'debit': 0.0,
                        'credit': rec.preliminary_gurantee_amount,

                    })
                rec.move_id2 = move2.id
                rec.is_clear_gurantee = True

    @api.constrains('project_id')
    def _project_id(self):
        if self.project_id:
            preliminary = self.env['preliminary.gurantee'].search(
                [('id', '!=', self.id), ('project_id', '=', self.project_id.id)])
            if preliminary:
                raise UserError(_('You Have Preliminary Gurantee For This Project'))

    def confirm_quotation(self):
        for rec in self:
            move = self.env['account.move'].create({
                'journal_id': rec.journal_id.id,
                'date': rec.date,
                'project_id': rec.project_id.id,
                'ref': rec.number + '-' + rec.project_id.name  ,
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.bank_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'credit': rec.preliminary_gurantee_amount + rec.bank_commission,
                    'debit': 0.0,
                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.project_id.bank_commission.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': 0.0,
                    'debit': rec.bank_commission,
                })
            self.env['account.move.line'].with_context(check_move_validity=False).create(
                {
                    'move_id': move.id,
                    'account_id': rec.project_id.preliminary_guarantee.id,
                    'analytic_account_id': rec.project_id.analytic_account_id.id,
                    'name': rec.project_id.name,
                    'partner_id': rec.partner_id.id,
                    'credit': 0.0,
                    'debit': rec.preliminary_gurantee_amount,

                })
            rec.status = 'confirmed'
            rec.move_id = move.id
