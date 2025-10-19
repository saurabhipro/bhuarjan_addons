from odoo import models, fields, api, _
import json

class BhuDistrict(models.Model):
    _name = 'bhu.district'
    _description = 'District'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='District', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True, domain="[('country_id.name','=','India')]")
