from odoo import models, fields, api, _
import json

class BhuDistrict(models.Model):
    _name = 'bhu.district'
    _description = 'District'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='District', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True, domain="[('country_id.name','=','India')]")
    village_line_ids = fields.One2many('bhu.village.line', 'district_id', string="Village Line")

class BhuVillageLine(models.Model):
    _name = 'bhu.village.line'
    _description = 'Village Line'

    district_id = fields.Many2one('bhu.district')
    village_id = fields.Many2one('bhu.village', string="Village")
    village_domain = fields.Char(string="Vi Domain", compute="_compute_vi_domain")

    def _compute_display_name(self):
        for record in self:
            record.display_name = _("%s (%s)", record.village_id.name, record.district_id.name)

    @api.depends('district_id')
    def _compute_vi_domain(self):
        for rec in self:
            if rec.district_id:
                valid_village_ids = rec.district_id.village_line_ids.mapped('district_id').ids
                rec.village_domain = json.dumps([('id', 'in', valid_village_ids)])
            else:
                rec.village_domain = json.dumps([])


class BhuVillage(models.Model):
    _name = 'bhu.village'
    _description = 'Village'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Village Name / ग्राम का नाम', required=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True)
    pincode = fields.Char(string='Pincode / पिनकोड')
    population = fields.Integer(string='Population / जनसंख्या')
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4))
    is_tribal_area = fields.Boolean(string='Tribal Area / आदिवासी क्षेत्र')
    is_forest_area = fields.Boolean(string='Forest Area / वन क्षेत्र')


class BhuTehsil(models.Model):
    _name = 'bhu.tehsil'
    _description = 'Tehsil'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Tehsil Name / तहसील का नाम', required=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    code = fields.Char(string='Tehsil Code / तहसील कोड')
    headquarters = fields.Char(string='Headquarters / मुख्यालय')
    population = fields.Integer(string='Population / जनसंख्या')
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4))
    is_tribal_tehsil = fields.Boolean(string='Tribal Tehsil / आदिवासी तहसील')
    is_forest_tehsil = fields.Boolean(string='Forest Tehsil / वन तहसील')


class BhuDepartment(models.Model):
    _name = 'bhu.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Department Name', required=True)
    code = fields.Char(string='Department Code')
    description = fields.Text(string='Description')
    head_of_department = fields.Char(string='Head of Department')
    contact_number = fields.Char(string='Contact Number')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')

