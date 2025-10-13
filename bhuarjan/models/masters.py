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

    name = fields.Char(string='Name', required=True)

