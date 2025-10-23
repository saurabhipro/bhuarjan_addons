from odoo import models, fields, api, _
import json

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
    
    name = fields.Char(string='Village Name / ग्राम का नाम', required=True, tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True, tracking=True)
    pincode = fields.Char(string='Pincode / पिनकोड', tracking=True)
    population = fields.Integer(string='Population / जनसंख्या', tracking=True)
    area_hectares = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    is_tribal_area = fields.Boolean(string='Tribal Area / आदिवासी क्षेत्र', tracking=True)
    is_forest_area = fields.Boolean(string='Forest Area / वन क्षेत्र', tracking=True)


class BhuDepartment(models.Model):
    _name = 'bhu.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Department Name', required=True, tracking=True)
    code = fields.Char(string='Department Code', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    head_of_department = fields.Char(string='Head of Department', tracking=True)
    contact_number = fields.Char(string='Contact Number', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    address = fields.Text(string='Address', tracking=True)

