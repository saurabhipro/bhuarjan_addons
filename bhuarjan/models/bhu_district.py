from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BhuDistrict(models.Model):
    _name = 'bhu.district'
    _description = 'District / जिला'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='District Name / जिला का नाम', required=True, tracking=True)
    code = fields.Char(string='District Code / जिला कोड', tracking=True)
    state_id = fields.Many2one('res.country.state', string='State / राज्य', required=True, 
                              domain="[('country_id.name','=','India')]", tracking=True)
    
    # Related Records
    sub_division_ids = fields.One2many('bhu.sub.division', 'district_id', string='Sub Divisions / उपभाग')
    tehsil_ids = fields.One2many('bhu.tehsil', 'district_id', string='Tehsils / तहसील')
    circle_ids = fields.One2many('bhu.circle', 'district_id', string='Circles / सर्कल')
    village_ids = fields.One2many('bhu.village', 'district_id', string='Villages / ग्राम')
    
    # Computed Fields
    sub_division_count = fields.Integer(string='Sub Divisions Count', compute='_compute_counts')
    tehsil_count = fields.Integer(string='Tehsils Count', compute='_compute_counts')
    village_count = fields.Integer(string='Villages Count', compute='_compute_counts')
    
    @api.depends('sub_division_ids', 'tehsil_ids', 'village_ids')
    def _compute_counts(self):
        """Compute counts of related records"""
        for record in self:
            record.sub_division_count = len(record.sub_division_ids)
            record.tehsil_count = len(record.tehsil_ids)
            record.village_count = len(record.village_ids)
    
    @api.constrains('name', 'state_id')
    def _check_unique_district_per_state(self):
        """Ensure district name is unique within a state"""
        for district in self:
            if district.name and district.state_id:
                existing = self.search([
                    ('id', '!=', district.id),
                    ('name', '=', district.name),
                    ('state_id', '=', district.state_id.id)
                ])
                if existing:
                    raise ValidationError(_('District "%s" already exists in state "%s".') % 
                                        (district.name, district.state_id.name))
    
    def action_view_sub_divisions(self):
        """View sub divisions of this district"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub Divisions of %s') % self.name,
            'res_model': 'bhu.sub.division',
            'view_mode': 'list,form',
            'domain': [('district_id', '=', self.id)],
            'context': {'default_district_id': self.id}
        }
    
    def action_view_tehsils(self):
        """View tehsils of this district"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tehsils of %s') % self.name,
            'res_model': 'bhu.tehsil',
            'view_mode': 'list,form',
            'domain': [('district_id', '=', self.id)],
            'context': {'default_district_id': self.id}
        }
    
    def action_view_villages(self):
        """View villages of this district"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Villages of %s') % self.name,
            'res_model': 'bhu.village',
            'view_mode': 'list,form',
            'domain': [('district_id', '=', self.id)],
            'context': {'default_district_id': self.id}
        }
    

