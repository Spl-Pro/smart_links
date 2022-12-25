# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Accountmove(models.Model):
    _inherit = 'account.move'
    po_number = fields.Char('Po')
    reference = fields.Char('Reference')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    number = fields.Char(' Number')
    additional_number = fields.Char('Additional Number')
    vat_group_no = fields.Char('Group Vat Number')
    building_no = fields.Char('Building No')
    district = fields.Char('District')
    other_Buyer_id = fields.Char('Other Buyer ID')
    arabic_name =fields.Char('Arabic Name')
    cr =fields.Char('CR')
class Rescompany(models.Model):
    _inherit = 'res.company'
    arabic_name =fields.Char('Arabic Name')
    additional_number = fields.Char('Additional Number')
    building_no = fields.Char('Building No')
    vat_group_no = fields.Char('Group Vat Number')
    district = fields.Char('District')
    other_seller_id = fields.Char('Other Seller ID')

