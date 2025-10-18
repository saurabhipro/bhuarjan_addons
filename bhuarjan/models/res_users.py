from odoo import models, fields, api

class ResUserInherit(models.Model):
    _inherit = 'res.users'

    parent_id = fields.Many2one('res.users', string="Parent")
    district_id = fields.Many2one('bhu.district', string="District")
    village_ids = fields.Many2many('bhu.village.line', string="Villages")
    child_ids = fields.One2many('res.users', 'parent_id', string='Direct subordinates')
