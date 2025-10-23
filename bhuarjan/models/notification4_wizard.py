from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import datetime


class Notification4Wizard(models.TransientModel):
    _name = 'bhu.notification4.wizard'
    _description = 'Notification 4 Generation Wizard'
    
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन का विवरण', required=True)
    
    # Computed fields to show available surveys
    available_surveys = fields.Text(string='Available Surveys / उपलब्ध सर्वे', compute='_compute_available_surveys', readonly=True)
    survey_count = fields.Integer(string='Survey Count / सर्वे की संख्या', compute='_compute_survey_count')
    
    @api.onchange('district_id')
    def _onchange_district_id(self):
        """Reset tehsil and village when district changes"""
        if self.district_id:
            self.tehsil_id = False
            self.village_id = False
        else:
            self.tehsil_id = False
            self.village_id = False
    
    @api.onchange('tehsil_id')
    def _onchange_tehsil_id(self):
        """Reset village when tehsil changes"""
        if self.tehsil_id:
            self.village_id = False
        else:
            self.village_id = False
    
    @api.depends('village_id')
    def _compute_available_surveys(self):
        """Compute available surveys for the selected village"""
        for record in self:
            if record.village_id:
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('state', 'in', ['submitted', 'approved']),
                    ('notification4_generated', '=', False)
                ])
                if surveys:
                    survey_info = []
                    for survey in surveys:
                        survey_info.append(f"Survey: {survey.name}, Khasra: {survey.khasra_number}, Area: {survey.total_area} hectares")
                    record.available_surveys = '\n'.join(survey_info)
                else:
                    record.available_surveys = "No available surveys found for this village."
            else:
                record.available_surveys = "Please select a village to see available surveys."
    
    @api.depends('village_id')
    def _compute_survey_count(self):
        """Compute the number of available surveys"""
        for record in self:
            if record.village_id:
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('state', 'in', ['submitted', 'approved']),
                    ('notification4_generated', '=', False)
                ])
                record.survey_count = len(surveys)
            else:
                record.survey_count = 0
    
    @api.depends('village_id')
    def _compute_village_notification_status(self):
        """Check if village already has Notification 4"""
        for record in self:
            if record.village_id:
                existing_notification = self.env['bhu.notification4'].search([
                    ('village_id', '=', record.village_id.id),
                    ('state', 'in', ['draft', 'published'])
                ])
                record.has_existing_notification = len(existing_notification) > 0
            else:
                record.has_existing_notification = False
    
    has_existing_notification = fields.Boolean(string='Has Existing Notification', compute='_compute_village_notification_status', store=False)
    
    def action_generate_notification4(self):
        """Generate Notification 4 for the selected village"""
        self.ensure_one()
        
        if not self.village_id:
            raise UserError(_('Please select a village first.'))
        
        if not self.public_purpose:
            raise UserError(_('Please enter the public purpose.'))
        
        # Check if Notification 4 already exists for this village
        existing_notification = self.env['bhu.notification4'].search([
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['draft', 'published'])
        ])
        
        if existing_notification:
            raise UserError(_('Notification 4 already exists for village %s. Please use the existing notification or select a different village.') % self.village_id.name)
        
        # Get all available surveys for the village
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['submitted', 'approved']),
            ('notification4_generated', '=', False)
        ])
        
        if not surveys:
            raise UserError(_('No available surveys found for this village. All surveys may have already been used for notification generation.'))
        
        # Group surveys by khasra number
        khasra_groups = {}
        for survey in surveys:
            khasra = survey.khasra_number or 'Unknown'
            if khasra not in khasra_groups:
                khasra_groups[khasra] = []
            khasra_groups[khasra].append(survey)
        
        # Create Notification 4 for each khasra
        created_notifications = []
        for khasra, khasra_surveys in khasra_groups.items():
            # Create the notification
            notification = self.env['bhu.notification4'].create({
                'district_id': self.district_id.id,
                'tehsil_id': self.tehsil_id.id,
                'village_id': self.village_id.id,
                'public_purpose': self.public_purpose,
                'survey_ids': [(6, 0, [s.id for s in khasra_surveys])],
                'signature_place': self.district_id.name,
                'signature_date': fields.Date.today(),
            })
            
            # Commit the transaction to ensure the record is saved
            self.env.cr.commit()
            
            # Refresh the record to get the ID
            notification.refresh()
            
            # Generate land details for this notification
            notification._generate_land_details()
            
            # Mark surveys as notification4_generated
            for survey in khasra_surveys:
                survey.notification4_generated = True
                survey.state = 'locked'  # Lock the survey
            
            created_notifications.append(notification)
        
        # Generate and download PDF automatically
        if created_notifications:
            return {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'bhuarjan.notification4_report',
                'context': {'active_ids': [n.id for n in created_notifications]},
                'name': _('Generated Notification 4 Reports'),
            }
        else:
            raise UserError(_('No notifications were created.'))
    
    def action_view_available_surveys(self):
        """View available surveys for the selected village"""
        self.ensure_one()
        
        if not self.village_id:
            raise UserError(_('Please select a village first.'))
        
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ['submitted', 'approved']),
            ('notification4_generated', '=', False)
        ])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Available Surveys'),
                'message': _('Found %d available surveys for village %s.') % (len(surveys), self.village_id.name),
                'type': 'info',
                'sticky': False,
            }
        }
