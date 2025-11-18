# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TreeMaster(models.Model):
    _name = 'bhu.tree.master'
    _description = 'Tree Master / वृक्ष मास्टर'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Tree Name / वृक्ष का नाम', required=True, tracking=True,
                      help='Name of the tree species (e.g., Mango, Neem, Banyan)')
    code = fields.Char(string='Tree Code / वृक्ष कोड', tracking=True,
                      help='Unique code for the tree')
    
    # Rates by development stage
    undeveloped_rate = fields.Float(string='Undeveloped Rate / अविकसित दर', digits=(16, 2), required=True, tracking=True,
                                   help='Compensation rate per undeveloped tree', default=0.0)
    semi_developed_rate = fields.Float(string='Semi-developed Rate / अर्ध-विकसित दर', digits=(16, 2), required=True, tracking=True,
                                      help='Compensation rate per semi-developed tree', default=0.0)
    fully_developed_rate = fields.Float(string='Fully Developed Rate / पूर्ण विकसित दर', digits=(16, 2), required=True, tracking=True,
                                       help='Compensation rate per fully developed tree', default=0.0)
    
    currency_id = fields.Many2one('res.currency', string='Currency / मुद्रा', 
                                 default=lambda self: self.env.company.currency_id)
    description = fields.Text(string='Description / विवरण', tracking=True)
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tree name must be unique!')
    ]

    @api.constrains('undeveloped_rate', 'semi_developed_rate', 'fully_developed_rate')
    def _check_rates_positive(self):
        """Ensure all rates are positive"""
        for record in self:
            if record.undeveloped_rate and record.undeveloped_rate < 0:
                raise ValidationError('Undeveloped rate must be positive or zero.')
            if record.semi_developed_rate and record.semi_developed_rate < 0:
                raise ValidationError('Semi-developed rate must be positive or zero.')
            if record.fully_developed_rate and record.fully_developed_rate < 0:
                raise ValidationError('Fully developed rate must be positive or zero.')

