from odoo import models, fields, api, _

class BhuVillage(models.Model):
    _name = 'bhu.village'
    _description = 'Village'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]

    state_id = fields.Many2one('res.country.state', string='State', required=True, domain=lambda self: self._get_state_domain())
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True)
    circle_id = fields.Many2one('bhu.circle', string='Circle / circle', required=True)
    name = fields.Char(string='Village Name / ग्राम का नाम', required=True)
    pincode = fields.Char(string='Pincode / पिनकोड')
    population = fields.Integer(string='Population / जनसंख्या')
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4))
    is_tribal_area = fields.Boolean(string='Tribal Area / आदिवासी क्षेत्र')
    is_forest_area = fields.Boolean(string='Forest Area / वन क्षेत्र')



