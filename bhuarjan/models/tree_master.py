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
    
    # Tree Type
    tree_type = fields.Selection([
        ('fruit_bearing', 'Fruit-bearing / फलदार'),
        ('non_fruit_bearing', 'Non-fruit-bearing / गैर-फलदार')
    ], string='Tree Type / वृक्ष प्रकार', required=True, default='non_fruit_bearing', tracking=True,
       help='Fruit-bearing trees have flat rates. Non-fruit-bearing trees have rates based on girth and development stage.')
    
    # Rate for fruit-bearing trees (flat rate, no girth or development stage dependency)
    rate = fields.Float(string='Rate / दर', digits=(16, 2), tracking=True,
                          help='Flat rate for fruit-bearing trees (not applicable for non-fruit-bearing trees)')
    
    # One2many for non-fruit-bearing tree rates
    tree_rate_ids = fields.One2many('bhu.tree.rate.master', 'tree_master_id', 
                                    string='Tree Rates / वृक्ष दरें',
                                    help='Girth-based rates for non-fruit-bearing trees')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tree name must be unique!')
    ]

    @api.constrains('rate')
    def _check_rates_positive(self):
        """Ensure all rates are positive"""
        for record in self:
            if record.tree_type == 'fruit_bearing':
                if record.rate and record.rate < 0:
                    raise ValidationError('Rate for fruit-bearing trees must be positive or zero.')
    
    @api.constrains('tree_type', 'rate')
    def _check_fruit_bearing_rate(self):
        """Ensure fruit-bearing trees have a rate"""
        for record in self:
            if record.tree_type == 'fruit_bearing' and not record.rate:
                raise ValidationError('Fruit-bearing trees must have a rate defined.')

