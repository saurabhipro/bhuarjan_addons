from odoo import models, fields, api, _
import uuid

class BhuVillage(models.Model):
    _name = 'bhu.village'
    _description = 'Village'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]

    village_uuid = fields.Char(string='Village UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    state_id = fields.Many2one('res.country.state', string='State', tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', tracking=True)
    circle_id = fields.Many2one('bhu.circle', string='Circle / circle', tracking=True)
    name = fields.Char(string='Village Name / ग्राम का नाम', required=True)
    pincode = fields.Char(string='Pincode / पिनकोड', tracking=True)
    population = fields.Integer(string='Population / जनसंख्या', tracking=True)
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4))
    is_tribal_area = fields.Boolean(string='Tribal Area / आदिवासी क्षेत्र', tracking=True)
    is_forest_area = fields.Boolean(string='Forest Area / वन क्षेत्र', tracking=True)



