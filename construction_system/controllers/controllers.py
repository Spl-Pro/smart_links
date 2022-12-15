# -*- coding: utf-8 -*-
from odoo import http

# class ConstructionSystem(http.Controller):
#     @http.route('/construction_system/construction_system/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/construction_system/construction_system/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('construction_system.listing', {
#             'root': '/construction_system/construction_system',
#             'objects': http.request.env['construction_system.construction_system'].search([]),
#         })

#     @http.route('/construction_system/construction_system/objects/<model("construction_system.construction_system"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('construction_system.object', {
#             'object': obj
#         })