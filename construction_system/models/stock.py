# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime


class ProjectStock(models.Model):
    _name = 'project.stock'
    _rec_name = 'number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    number = fields.Char(readonly=True)
    status = fields.Selection(string="Status", selection=[('draft', 'Draft'), ('confirmed', 'Approved')],
                              default='draft')
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    project_type = fields.Selection(string="Project Types", selection=[('internal_project', 'Internal Project'),
                                                                       ('customer_project', 'Customer Project'), ],
                                   related='project_id.project_type', required=False, )
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer", )
    warehouse_id = fields.Many2one('stock.warehouse')
    expire_date = fields.Datetime('Creation Date',required=True,default=datetime.today())
    date = fields.Datetime('Schedual Date')
    location_id = fields.Many2one('stock.location', string='Project Location',)
    source_location_id = fields.Many2one('stock.location', string='Source Location',
                                         compute='compute_source_project_location')
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    work_item = fields.Many2one('product.product', 'Work Item')
    project_stock_line_ids = fields.One2many("project.stock.line", "project_stock_id", string="Project Stock", )
    project_move_line_ids = fields.One2many("project.move.line", "project_stock_id", string="Project Stock", )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        location =self.env['stock.location'].search([('name','=',self.project_id.name)])
        self.location_id = location.id
        res = {}
        require_ids = []
        for rec in self:
            for line in rec.project_id.bid_requirement_ids:
                require_ids.append(line.wcateg_id.id)
            if len(require_ids) > 0:
                res['domain'] = {'wcateg_id': [('id', 'in', require_ids)]}
            else:
                res['domain'] = {'wcateg_id': [('id', '=', False)]}
        return res

    @api.onchange('project_id', 'wcateg_id')
    def _onchange_partner_id_categ(self):
        res = {}
        work_item_ids = []
        for rec in self:
            for line in rec.project_id.bid_requirement_ids:
                if rec.wcateg_id == line.wcateg_id:
                    work_item_ids.append(line.product_id.id)
            if len(work_item_ids) > 0:
                res['domain'] = {'work_item': [('id', 'in', work_item_ids)]}
            else:
                res['domain'] = {'work_item': [('id', '=', False)]}
        return res

    @api.onchange('project_id')
    def _onchange_partner_id_item(self):
        res = {}
        require_ids = []
        for rec in self:
            for line in rec.project_id.bid_requirement_ids:
                require_ids.append(line.product_id.id)
            if len(require_ids) > 0:
                res['domain'] = {'work_item': [('id', 'in', require_ids)]}
            else:
                res['domain'] = {'work_item': [('id', '=', False)]}
        return res

    @api.depends('warehouse_id')
    def compute_source_project_location(self):
        for rec in self:
            rec.source_location_id =0
            if rec.warehouse_id:
                wh_location = self.env['stock.location'].search([('location_id.name', '=', rec.warehouse_id.code)])
                rec.source_location_id = wh_location.id

    def confirm_quotation(self):
        for rec in self:
            picking_type_id =0
            if rec.project_type =='internal_project':
                picking_type= self.env['stock.picking.type'].search([('code','=','internal')])
                picking_type_id =picking_type.id
            else:
                picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')])
                picking_type_id = picking_type.id
            stock = self.env['stock.picking'].create({
                "picking_type_id": picking_type_id,
                "location_id": rec.source_location_id.id,
                "location_dest_id": rec.location_id.id,
                # "project_id": rec.project_id.id,
            })
            for line in rec.project_stock_line_ids:
                if line.qty_available >= line.qty_uos and line.qty_available !=0.0 :
                    move = self.env['stock.move'].create({
                        "picking_id": stock.id,
                        "product_id": line.product_id.id,
                        "product_uom": line.product_id.uom_id.id,
                        "product_uom_qty": line.qty_uos,
                        "name": line.product_id.name,
                        "location_id": rec.source_location_id.id,
                        "location_dest_id": rec.location_id.id,
                        "project_id": rec.project_id.id,
                    })
                    stock.state ='done'
                    move2 = self.env['project.move.line'].create({
                        'project_stock_id': self.id,
                        'stock_move_id': stock.id,
                    })
                    rec.status = 'confirmed'
                else:
                    raise UserError( _('This Product Quantity ON The location Less Than : %s')
                                     % (line.qty_uos))

    # @api.depends('partner_id', 'project_id')
    # def compute_project_location(self):
    #     for rec in self:
    #         if rec.partner_id:
    #             location = self.env['stock.location'].search(
    #                 [('project_id', '=', rec.project_id.id), ('usage', '=', 'customer'),
    #                  ('customer', '=', rec.partner_id.id)])
    #
    #             rec.location_id = location.id

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('project.stock')
        vals['number'] = sequence or '/'
        return super(ProjectStock, self).create(vals)


class ProjectStockLine(models.Model):
    _name = 'project.stock.line'
    project_stock_id = fields.Many2one('project.stock', string="Project Stock")
    wcateg_id = fields.Many2one('project.works.category', string='Work Category')
    product_id = fields.Many2one('product.product', string='Product')
    qty_available = fields.Float(string='Qty On Source',
                                 compute='compute_qty_available')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Product Uom')
    qty_uos = fields.Float(string='Quantity UOS')

    @api.depends('product_id')
    def compute_qty_available(self):
        for rec in self:
            rec.qty_available = 0.0
            if rec.project_stock_id.source_location_id:
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.project_stock_id.source_location_id.id)])
                x = 0.0
                for line in stock_quant:
                    print(line.id)
                    x= x+line.quantity
                rec.qty_available =x


class StockLocation(models.Model):
    _inherit = 'stock.location'
    project_id = fields.Many2one('project.project', string='Project', domain=[('awarded', '=', True)])
    customer = fields.Many2one(related='project_id.partner_id', string='Customer')


class MaterialInfo(models.Model):
    _name = 'project.move.line'
    project_stock_id = fields.Many2one('project.stock', string="Project Stock")
    stock_move_id = fields.Many2one('stock.move', string='Stock Move')
class JournalMove(models.Model):
    _name = 'account.move.journal'
    project_stock_id = fields.Many2one('project.stock', string="Project Stock")
    stock_move_id = fields.Many2one('stock.move', string='Stock Move')


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        res=super(StockQuant, self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id,)
        for r in res:
            if move.project_id:
                if r[2]['debit'] > 0:
                    r[2]['analytic_account_id'] = move.project_id.analytic_account_id.id
                    r[2]['account_id'] = move.project_id.project_material_cost.id

        return res


    def _create_account_move_line(self, cr, uid, quants, move, credit_account_id, debit_account_id, journal_id, context=None):
        #group quants by cost
        quant_cost_qty = {}
        for quant in quants:
            if quant_cost_qty.get(quant.cost):
                quant_cost_qty[quant.cost] += quant.qty
            else:
                quant_cost_qty[quant.cost] = quant.qty
        move_obj = self.pool.get('account.move')
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
            period_id = context.get('force_period', self.pool.get('account.period').find(cr, uid, context=context)[0])
            x=move_obj.create(cr, uid, {'journal_id': journal_id,
                                      'line_id': move_lines,
                                      'period_id': period_id,
                                      'project_id': move.project_id.id,
                                      'ref': move.picking_id.name}, context=context)





class StockMove(models.Model):
    _inherit = 'stock.move'
    project_id = fields.Many2one('project.project', string="Project")

