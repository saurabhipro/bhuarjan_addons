from odoo import models, fields, api, _

class BhuTehsil(models.Model):
    _name = 'bhu.tehsil'
    _description = 'Tehsil'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Tehsil Name / तहसील का नाम', required=True)

    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]
            
    state_id = fields.Many2one('res.country.state', string='State', tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', tracking=True)
    code = fields.Char(string='Tehsil Code / तहसील कोड', tracking=True)
    headquarters = fields.Char(string='Headquarters / मुख्यालय', tracking=True)
    population = fields.Integer(string='Population / जनसंख्या', tracking=True)
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    is_tribal_tehsil = fields.Boolean(string='Tribal Tehsil / आदिवासी तहसील', tracking=True)
    is_forest_tehsil = fields.Boolean(string='Forest Tehsil / वन तहसील', tracking=True)
