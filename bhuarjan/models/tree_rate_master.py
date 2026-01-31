# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TreeMaster(models.Model):
    _name = 'bhu.tree.master'
    _description = 'Tree Rate Master / वृक्ष दर मास्टर'
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
    
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    
    # One2many for tree rate variants (same structure for both fruit and non-fruit bearing)
    tree_rate_ids = fields.One2many('bhu.tree.rate.master', 'tree_master_id', 
                                    string='Rate Variants / दर वेरिएंट',
                                    help='Rate variants based on development stage and girth range for all tree types')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tree name must be unique!')
    ]


class TreeRateMaster(models.Model):
    _name = 'bhu.tree.rate.master'
    _description = 'Tree Rate Master - Rate Variants'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tree_master_id, development_stage, girth_range_min'

    tree_master_id = fields.Many2one('bhu.tree.master', string='Tree / वृक्ष', required=True, ondelete='cascade', tracking=True)
    development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित')
    ], string='Development Stage / विकास स्तर', required=True, tracking=True)
    
    girth_range_min = fields.Float(string='Min Girth (cm) / न्यूनतम छाती (से.मी.)', required=True, tracking=True,
                                   help='Minimum girth in centimeters')
    girth_range_max = fields.Float(string='Max Girth (cm) / अधिकतम छाती (से.मी.)', tracking=True,
                                   help='Maximum girth in centimeters. Leave empty for "Above X cm"')
    
    rate = fields.Monetary(string='Rate / दर', currency_field='currency_id', required=True, tracking=True,
                          help='Compensation rate for this tree variant')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.INR'))
    
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)
    description = fields.Text(string='Description / विवरण', tracking=True,
                              help='Additional description or notes for this rate variant')

    _sql_constraints = [
        ('unique_tree_rate', 'unique(tree_master_id, development_stage, girth_range_min, girth_range_max)',
         'A rate variant with the same tree, development stage, and girth range already exists!')
    ]
