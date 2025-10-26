# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _


class LandType(models.Model):
    _name = 'bhu.land.type'
    _description = 'Land Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Land Type', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Land Type code must be unique!')
    ]


class RateMaster(models.Model):
    _name = 'bhu.rate.master'
    _description = 'Rate Master - Land Valuation Rates'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Status', default='draft', tracking=True)

    # Location Information
    district_id = fields.Many2one('bhu.district', string='District', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True, tracking=True)
    
    # Land Classification
    land_type_id = fields.Many2one('bhu.land.type', string='Land Type', required=True, tracking=True)
    irrigation_status = fields.Selection([
        ('irrigated', 'Irrigated'),
        ('non_irrigated', 'Non-Irrigated'),
        ('partially_irrigated', 'Partially Irrigated')
    ], string='Irrigation Status', required=True, tracking=True)
    
    # Road Proximity
    road_proximity = fields.Selection([
        ('close_to_road', 'Close to Road (0-100m)'),
        ('near_road', 'Near Road (100-500m)'),
        ('far_from_road', 'Far from Road (500m+)')
    ], string='Road Proximity', required=True, tracking=True)
    
    # Rate Information
    rate_per_hectare = fields.Monetary(string='Rate per Hectare', currency_field='currency_id', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Additional Factors
    soil_quality = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Soil Quality', tracking=True)
    
    # Market Factors
    market_demand = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], string='Market Demand', tracking=True)
    
    # Effective Dates
    effective_from = fields.Date(string='Effective From', required=True, default=fields.Date.today, tracking=True)
    effective_to = fields.Date(string='Effective To', tracking=True)
    
    # Additional Information
    remarks = fields.Text(string='Remarks', tracking=True)
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_name = fields.Char(related='company_id.name', string='Company Name', store=True)
    
    # Computed Fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    @api.depends('district_id', 'village_id', 'land_type_id', 'irrigation_status', 'road_proximity')
    def _compute_display_name(self):
        for record in self:
            if record.district_id and record.village_id and record.land_type_id:
                record.display_name = f"{record.district_id.name} - {record.village_id.name} - {record.land_type_id.name}"
            else:
                record.display_name = record.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.rate.master') or _('New')
        return super(RateMaster, self).create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_deactivate(self):
        self.write({'state': 'inactive'})

    def action_reset(self):
        self.write({'state': 'draft'})

    @api.model
    def get_rate_for_land(self, district_id, village_id, land_type_id, irrigation_status, road_proximity):
        """Get the current rate for specific land parameters"""
        domain = [
            ('district_id', '=', district_id),
            ('village_id', '=', village_id),
            ('land_type_id', '=', land_type_id),
            ('irrigation_status', '=', irrigation_status),
            ('road_proximity', '=', road_proximity),
            ('state', '=', 'active'),
            ('effective_from', '<=', fields.Date.today()),
            '|',
            ('effective_to', '=', False),
            ('effective_to', '>=', fields.Date.today())
        ]
        
        rate_record = self.search(domain, limit=1)
        return rate_record.rate_per_hectare if rate_record else 0.0

    @api.model
    def get_all_rates_for_village(self, village_id):
        """Get all active rates for a specific village"""
        domain = [
            ('village_id', '=', village_id),
            ('state', '=', 'active'),
            ('effective_from', '<=', fields.Date.today()),
            '|',
            ('effective_to', '=', False),
            ('effective_to', '>=', fields.Date.today())
        ]
        
        return self.search(domain)

    @api.model
    def get_rate_summary_by_district(self, district_id):
        """Get rate summary for all villages in a district"""
        domain = [
            ('district_id', '=', district_id),
            ('state', '=', 'active'),
            ('effective_from', '<=', fields.Date.today()),
            '|',
            ('effective_to', '=', False),
            ('effective_to', '>=', fields.Date.today())
        ]
        
        return self.search(domain)
