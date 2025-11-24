# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AppVersion(models.Model):
    _name = 'bhu.app.version'
    _description = 'App Version Control / ऐप संस्करण नियंत्रण'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Version Name / संस्करण नाम', required=True, tracking=True,
                      help='Version identifier (e.g., 1.0.0, 2.1.3)')
    version_code = fields.Integer(string='Version Code / संस्करण कोड', required=True, tracking=True,
                                  help='Numeric version code for comparison (e.g., 1, 2, 10, 100)')
    is_active = fields.Boolean(string='Is Active / सक्रिय है', default=True, tracking=True,
                              help='If active, users with this version can use the app')
    is_latest = fields.Boolean(string='Is Latest / नवीनतम है', default=False, tracking=True,
                              help='Mark this as the latest version')
    activated_date = fields.Datetime(string='Activated Date / सक्रिय तिथि', readonly=True, tracking=True,
                                    help='Date when this version was activated')
    deactivated_date = fields.Datetime(string='Deactivated Date / निष्क्रिय तिथि', readonly=True, tracking=True,
                                      help='Date when this version was deactivated')
    description = fields.Text(string='Description / विवरण', tracking=True,
                             help='Release notes or description for this version')
    force_update = fields.Boolean(string='Force Update / बलपूर्वक अपडेट', default=False, tracking=True,
                                  help='If enabled, users must update to this version to continue using the app')
    
    # Statistics
    active_user_count = fields.Integer(string='Active Users / सक्रिय उपयोगकर्ता', compute='_compute_active_user_count',
                                      help='Number of users currently using this version')
    
    _sql_constraints = [
        ('version_code_unique', 'unique(version_code)', 'Version code must be unique!'),
        ('name_unique', 'unique(name)', 'Version name must be unique!'),
    ]

    @api.depends('name')
    def _compute_active_user_count(self):
        """Compute number of active users for this version"""
        for record in self:
            # This would need to be implemented based on your user session tracking
            # For now, we'll set it to 0
            record.active_user_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle auto-disable of old versions and set activation date"""
        for vals in vals_list:
            # Set activation date if is_active is True
            if vals.get('is_active', True):
                vals['activated_date'] = fields.Datetime.now()
            
            # If this is marked as latest, unmark other latest versions
            if vals.get('is_latest', False):
                self.env['bhu.app.version'].search([('is_latest', '=', True)]).write({'is_latest': False})
            
            # If this is active and latest, disable other active versions
            if vals.get('is_active', True) and vals.get('is_latest', False):
                old_versions = self.env['bhu.app.version'].search([
                    ('is_active', '=', True),
                    ('id', '!=', False)  # Will be set after creation
                ])
                for old_version in old_versions:
                    old_version.write({
                        'is_active': False,
                        'deactivated_date': fields.Datetime.now()
                    })
        
        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle activation/deactivation dates"""
        for record in self:
            # Handle activation
            if 'is_active' in vals:
                if vals['is_active'] and not record.is_active:
                    # Activating
                    vals['activated_date'] = fields.Datetime.now()
                    vals['deactivated_date'] = False
                    
                    # If this is being activated and is latest, disable other active versions
                    if record.is_latest:
                        other_active = self.env['bhu.app.version'].search([
                            ('is_active', '=', True),
                            ('is_latest', '=', True),
                            ('id', '!=', record.id)
                        ])
                        for other in other_active:
                            other.write({
                                'is_active': False,
                                'deactivated_date': fields.Datetime.now()
                            })
                elif not vals['is_active'] and record.is_active:
                    # Deactivating
                    vals['deactivated_date'] = fields.Datetime.now()
            
            # Handle latest flag
            if 'is_latest' in vals and vals['is_latest']:
                # Unmark other latest versions
                self.env['bhu.app.version'].search([
                    ('is_latest', '=', True),
                    ('id', '!=', record.id)
                ]).write({'is_latest': False})
        
        return super().write(vals)

    @api.constrains('version_code')
    def _check_version_code(self):
        """Ensure version code is positive"""
        for record in self:
            if record.version_code <= 0:
                raise ValidationError(_('Version code must be greater than 0.'))

    def action_activate(self):
        """Activate this version and deactivate others"""
        self.ensure_one()
        # Deactivate all other active versions
        other_active = self.env['bhu.app.version'].search([
            ('is_active', '=', True),
            ('id', '!=', self.id)
        ])
        other_active.write({
            'is_active': False,
            'deactivated_date': fields.Datetime.now()
        })
        
        # Activate this version
        self.write({
            'is_active': True,
            'activated_date': fields.Datetime.now(),
            'deactivated_date': False
        })
        
        return True

    def action_deactivate(self):
        """Deactivate this version"""
        self.ensure_one()
        self.write({
            'is_active': False,
            'deactivated_date': fields.Datetime.now()
        })
        
        # TODO: Trigger logout for all users using this version
        # This would require implementing a session tracking mechanism
        
        return True

    def action_set_as_latest(self):
        """Set this version as latest"""
        self.ensure_one()
        # Unmark other latest versions
        self.env['bhu.app.version'].search([
            ('is_latest', '=', True),
            ('id', '!=', self.id)
        ]).write({'is_latest': False})
        
        # Mark this as latest
        self.write({'is_latest': True})
        
        return True

    @api.model
    def get_latest_version(self):
        """Get the latest active version"""
        latest = self.search([('is_latest', '=', True), ('is_active', '=', True)], limit=1)
        if not latest:
            # Fallback to highest version code
            latest = self.search([('is_active', '=', True)], order='version_code desc', limit=1)
        return latest

    @api.model
    def check_version_status(self, version_code):
        """Check if a version is allowed to be used"""
        version = self.search([('version_code', '=', version_code)], limit=1)
        if not version:
            return {
                'allowed': False,
                'message': 'Version not found. Please install the latest version.',
                'latest_version': None
            }
        
        latest = self.get_latest_version()
        
        if not version.is_active:
            return {
                'allowed': False,
                'message': f'This version ({version.name}) is no longer supported. Please install the latest version {latest.name if latest else "N/A"}.',
                'latest_version': {
                    'name': latest.name if latest else None,
                    'version_code': latest.version_code if latest else None,
                    'force_update': latest.force_update if latest else False
                } if latest else None
            }
        
        # Check if there's a newer version available
        if latest and latest.version_code > version.version_code:
            return {
                'allowed': True,
                'message': f'A new version ({latest.name}) is available. Please update for the best experience.',
                'latest_version': {
                    'name': latest.name,
                    'version_code': latest.version_code,
                    'force_update': latest.force_update
                },
                'update_available': True
            }
        
        return {
            'allowed': True,
            'message': 'Version is valid.',
            'latest_version': {
                'name': latest.name if latest else version.name,
                'version_code': latest.version_code if latest else version.version_code,
                'force_update': latest.force_update if latest else False
            } if latest else None
        }

