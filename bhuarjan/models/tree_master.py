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
       help='Type of tree. Both types use rate variants based on development stage and girth range.')
    
    # One2many for tree rate variants (same structure for both fruit and non-fruit bearing)
    tree_rate_ids = fields.One2many('bhu.tree.rate.master', 'tree_master_id', 
                                    string='Rate Variants / दर वेरिएंट',
                                    help='Rate variants based on development stage and girth range for all tree types')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tree name must be unique!')
    ]

