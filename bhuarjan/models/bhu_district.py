from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class BhuDistrict(models.Model):
    _name = 'bhu.district'
    _description = 'District / जिला'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='District Name / जिला का नाम', required=True, tracking=True)
    code = fields.Char(string='District Code / जिला कोड', tracking=True)
    state_id = fields.Many2one('res.country.state', string='State / राज्य', required=True, 
                              domain="[('country_id.name','=','India')]", tracking=True)
    
    # Company/Organization Information (1:1 Mapping)
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # District Type and Classification
    district_type = fields.Selection([
        ('administrative', 'Administrative District / प्रशासनिक जिला'),
        ('revenue', 'Revenue District / राजस्व जिला'),
        ('forest', 'Forest District / वन जिला'),
        ('tribal', 'Tribal District / आदिवासी जिला')
    ], string='District Type / जिला प्रकार', default='administrative', tracking=True)
    
    # 1:1 Mapping Fields
    is_company_created = fields.Boolean(string='Company Created / कंपनी बनाई गई', default=False, readonly=True)
    company_name = fields.Char(string='Company Name / कंपनी का नाम', compute='_compute_company_name', store=True)
    
    # Geographic Information
    latitude = fields.Float(string='Latitude / अक्षांश', digits=(10, 8), tracking=True)
    longitude = fields.Float(string='Longitude / देशांतर', digits=(11, 8), tracking=True)
    area_sq_km = fields.Float(string='Area (Sq. Km) / क्षेत्रफल (वर्ग किमी)', digits=(10, 2), tracking=True)
    population = fields.Integer(string='Population / जनसंख्या', tracking=True)
    
    # Administrative Information
    collector_name = fields.Char(string='Collector Name / कलेक्टर का नाम', tracking=True)
    collector_contact = fields.Char(string='Collector Contact / कलेक्टर संपर्क', tracking=True)
    headquarters = fields.Char(string='Headquarters / मुख्यालय', tracking=True)
    
    # Status and Classification
    is_tribal_district = fields.Boolean(string='Tribal District / आदिवासी जिला', default=False, tracking=True)
    is_forest_district = fields.Boolean(string='Forest District / वन जिला', default=False, tracking=True)
    is_naxal_affected = fields.Boolean(string='Naxal Affected / नक्सल प्रभावित', default=False, tracking=True)
    
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
    
    @api.depends('company_id', 'name')
    def _compute_company_name(self):
        """Compute company name from district"""
        for record in self:
            if record.company_id:
                record.company_name = record.company_id.name
            else:
                record.company_name = f"{record.name} District Office"
    
    @api.constrains('name', 'state_id', 'company_id')
    def _check_unique_district_per_state_company(self):
        """Ensure district name is unique within a state and company"""
        for district in self:
            if district.name and district.state_id and district.company_id:
                existing = self.search([
                    ('id', '!=', district.id),
                    ('name', '=', district.name),
                    ('state_id', '=', district.state_id.id),
                    ('company_id', '=', district.company_id.id)
                ])
                if existing:
                    raise ValidationError(_('District "%s" already exists in state "%s" for company "%s".') % 
                                        (district.name, district.state_id.name, district.company_id.name))
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-create company for each district (1:1 mapping)"""
        for vals in vals_list:
            # Create company if not provided
            if 'company_id' not in vals or not vals.get('company_id'):
                company_name = f"{vals.get('name', 'District')} District Office"
                company = self.env['res.company'].create({
                    'name': company_name,
                    'currency_id': self.env.ref('base.INR').id,
                    'country_id': self.env.ref('base.in').id,
                    'state_id': vals.get('state_id'),
                })
                
                # Add company to current user's company access
                current_user = self.env.user
                if company not in current_user.company_ids:
                    current_user.write({
                        'company_ids': [(4, company.id)]
                    })
                
                vals['company_id'] = company.id
                vals['is_company_created'] = True
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to handle company updates"""
        for record in self:
            # If district name changes, update company name
            if 'name' in vals and record.company_id and record.is_company_created:
                new_company_name = f"{vals['name']} District Office"
                record.company_id.write({'name': new_company_name})
        
        return super().write(vals)
    
    def action_create_company(self):
        """Manually create company for district (1:1 mapping)"""
        for record in self:
            if not record.is_company_created:
                company_name = f"{record.name} District Office"
                company = self.env['res.company'].create({
                    'name': company_name,
                    'currency_id': self.env.ref('base.INR').id,
                    'country_id': self.env.ref('base.in').id,
                    'state_id': record.state_id.id,
                })
                
                # Add company to current user's company access
                current_user = self.env.user
                if company not in current_user.company_ids:
                    current_user.write({
                        'company_ids': [(4, company.id)]
                    })
                
                record.write({
                    'company_id': company.id,
                    'is_company_created': True
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Company Created'),
                        'message': _('Company "%s" created for district "%s" and added to your company access.') % (company_name, record.name),
                        'type': 'success',
                    }
                }
        return False
    
    @api.model
    def get_districts_by_company(self, company_id=None):
        """Get districts for a specific company (1:1 mapping)"""
        if not company_id:
            company_id = self.env.company.id
        return self.search([('company_id', '=', company_id)])
    
    @api.model
    def switch_to_district(self, district_id):
        """Switch to a specific district (change company context)"""
        district = self.browse(district_id)
        if district.exists():
            # Ensure user has access to the company
            current_user = self.env.user
            if district.company_id not in current_user.company_ids:
                current_user.write({
                    'company_ids': [(4, district.company_id.id)]
                })
            
            # Switch company context
            self.env.user.company_id = district.company_id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('District Switched'),
                    'message': _('Switched to district: %s') % district.name,
                    'type': 'success',
                }
            }
        return False
    
    def action_switch_company(self):
        """Action to switch company and refresh the view"""
        for record in self:
            if record.company_id:
                # Switch to the district's company
                self.env.user.company_id = record.company_id
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
        return False
    
    def action_fix_company_access(self):
        """Fix company access for all districts"""
        current_user = self.env.user
        districts = self.search([])
        companies_added = []
        
        for district in districts:
            if district.company_id and district.company_id not in current_user.company_ids:
                current_user.write({
                    'company_ids': [(4, district.company_id.id)]
                })
                companies_added.append(district.company_id.name)
        
        if companies_added:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Company Access Fixed'),
                    'message': _('Added %d companies to your access: %s') % (len(companies_added), ', '.join(companies_added)),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Company Access'),
                    'message': _('All district companies are already in your access.'),
                    'type': 'info',
                }
            }
    
    def action_assign_to_current_company(self):
        """Assign districts to current company"""
        current_company = self.env.company
        updated_districts = []
        
        for record in self:
            if record.company_id != current_company:
                record.write({
                    'company_id': current_company.id,
                    'is_company_created': False  # Reset since we're assigning to existing company
                })
                updated_districts.append(record.name)
        
        if updated_districts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Districts Updated'),
                    'message': _('Updated %d districts to current company: %s') % (len(updated_districts), ', '.join(updated_districts)),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Changes'),
                    'message': _('All selected districts are already assigned to current company.'),
                    'type': 'info',
                }
            }
    
    
    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        """Validate GPS coordinates"""
        for district in self:
            if district.latitude and (district.latitude < -90 or district.latitude > 90):
                raise ValidationError(_('Latitude must be between -90 and 90 degrees.'))
            if district.longitude and (district.longitude < -180 or district.longitude > 180):
                raise ValidationError(_('Longitude must be between -180 and 180 degrees.'))
    
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
    

