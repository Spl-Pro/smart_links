# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import csv
import base64
# import cStringIO
from datetime import datetime
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class AttendanceUpload(models.TransientModel):
    _name = 'bid.requirement.upload'
    # your file will be stored here:
    csv_file = fields.Binary(string='CSV File', required=True)
    project_id = fields.Many2one("project.project", string="Project", )


    def import_csv_file(self):
        bid_obj = self.env["bid.requirement"]
        try:
            val = base64.decodestring(self.csv_file)
            # input_file = cStringIO.StringIO(val)
            input_file = ''
            csv_reader = csv.DictReader(input_file, delimiter=',')
            for lines in csv_reader:
                if not lines:
                    raise UserError( _('Invalid File!.\nPlease try using another file.'))
                else:
                    if 'product' in lines and 'work_category' in lines and 'unit_cost' in lines and 'margin' in lines and 'quantity' in lines and 'sales_price' in lines:
                        product_id = self.env['product.product'].search([('product_tmpl_id.name', '=', lines['product'])])
                        if not product_id:
                            product_id = self.env['product.product'].create({'name': lines['product']})
                        wcateg_id = self.env['project.works.category'].search([('name', '=', lines['work_category'])])
                        if not wcateg_id:
                            wcateg_id = self.env['project.works.category'].create({'name': lines['work_category']})

                        bid_obj.create({
                            'project_id': self.project_id.id,
                            'product_id': product_id.id,
                            'wcateg_id': wcateg_id.id,
                            'margin': lines['margin'],
                            'qty': lines['quantity'],
                            'sales_price': lines['sales_price'],
                            'unit_cost': lines['unit_cost'],
                        })
                    else:
                        raise UserError(_('Wrong Bid Requirements file. Please import another one.'))

        except TypeError as e:
            raise UserError(_('Invalid File!.\nPlease try using another file.'))
