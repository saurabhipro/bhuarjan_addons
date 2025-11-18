# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TreeRateMaster(models.Model):
    _name = 'bhu.tree.rate.master'
    _description = 'Tree Rate Master - Girth-based Rates for Non-fruit-bearing Trees'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tree_master_id, girth_range_min, development_stage'

    tree_master_id = fields.Many2one('bhu.tree.master', string='Tree / वृक्ष', required=True, 
                                     domain="[('tree_type', '=', 'non_fruit_bearing')]", 
                                     tracking=True, ondelete='cascade',
                                     help='Select non-fruit-bearing tree from master')
    
    # Girth Range (in cm)
    girth_range_min = fields.Float(string='Min Girth (cm) / न्यूनतम छाती (से.मी.)', digits=(10, 2), 
                                   required=True, tracking=True,
                                   help='Minimum chest girth in centimeters')
    girth_range_max = fields.Float(string='Max Girth (cm) / अधिकतम छाती (से.मी.)', digits=(10, 2), 
                                  tracking=True,
                                  help='Maximum chest girth in centimeters (leave empty for "Above X cm")')
    
    # Development Stage
    development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित')
    ], string='Development Stage / विकास स्तर', required=True, tracking=True,
       help='Sound: Fully developed, Half Sound: Semi-developed, Un Sound: Undeveloped')
    
    # Rate
    rate = fields.Monetary(string='Rate / दर', currency_field='currency_id', 
                           digits=(16, 2), required=True, tracking=True,
                           help='Compensation rate for this girth range and development stage')
    currency_id = fields.Many2one('res.currency', string='Currency / मुद्रा', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Additional Info
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)
    description = fields.Text(string='Description / विवरण', tracking=True)

    _sql_constraints = [
        ('unique_tree_girth_stage', 'unique(tree_master_id, girth_range_min, girth_range_max, development_stage)', 
         'Rate already exists for this tree, girth range, and development stage combination!')
    ]

    @api.constrains('girth_range_min', 'girth_range_max')
    def _check_girth_range(self):
        """Ensure girth range is valid"""
        for record in self:
            if record.girth_range_min < 0:
                raise ValidationError('Minimum girth must be positive or zero.')
            if record.girth_range_max and record.girth_range_max <= record.girth_range_min:
                raise ValidationError('Maximum girth must be greater than minimum girth.')
    
    @api.constrains('tree_master_id', 'girth_range_min', 'girth_range_max')
    def _check_girth_overlap(self):
        """Ensure girth ranges don't overlap for the same tree and development stage"""
        for record in self:
            domain = [
                ('tree_master_id', '=', record.tree_master_id.id),
                ('development_stage', '=', record.development_stage),
                ('id', '!=', record.id),
                ('active', '=', True)
            ]
            existing = self.search(domain)
            for existing_record in existing:
                # Check for overlap
                if (record.girth_range_max is False or existing_record.girth_range_max is False):
                    # One is "Above X cm" - check if they overlap
                    if record.girth_range_max is False:
                        # Current is "Above X", existing has max
                        if existing_record.girth_range_max >= record.girth_range_min:
                            raise ValidationError(
                                f'Girth range overlaps with existing range: '
                                f'{existing_record.girth_range_min}-{existing_record.girth_range_max or "Above"} cm'
                            )
                    else:
                        # Existing is "Above X", current has max
                        if record.girth_range_max >= existing_record.girth_range_min:
                            raise ValidationError(
                                f'Girth range overlaps with existing range: '
                                f'{existing_record.girth_range_min}-{existing_record.girth_range_max or "Above"} cm'
                            )
                else:
                    # Both have max values - check overlap
                    if not (record.girth_range_max < existing_record.girth_range_min or 
                           record.girth_range_min > existing_record.girth_range_max):
                        raise ValidationError(
                            f'Girth range overlaps with existing range: '
                            f'{existing_record.girth_range_min}-{existing_record.girth_range_max} cm'
                        )
    
    @api.model
    def get_rate_for_tree(self, tree_master_id, girth_cm, development_stage):
        """Get rate for a tree based on girth and development stage"""
        domain = [
            ('tree_master_id', '=', tree_master_id),
            ('development_stage', '=', development_stage),
            ('girth_range_min', '<=', girth_cm),
            '|',
            ('girth_range_max', '=', False),
            ('girth_range_max', '>=', girth_cm),
            ('active', '=', True)
        ]
        rate_record = self.search(domain, limit=1, order='girth_range_min desc')
        return rate_record.rate if rate_record else 0.0

