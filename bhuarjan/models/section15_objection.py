# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class Section15Objection(models.Model):
    _name = 'bhu.section15.objection'
    _description = 'Section 15 Objections'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Objection Reference / आपत्ति संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner / भूमिस्वामी', required=True, tracking=True)
    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', tracking=True)
    filtered_landowner_ids = fields.Many2many('bhu.landowner', string='Filtered Landowners', compute='_compute_filtered_landowner_ids', store=False)
    filtered_survey_ids = fields.Many2many('bhu.survey', string='Filtered Surveys', compute='_compute_filtered_survey_ids', store=False)
    
    @api.depends('village_id')
    def _compute_filtered_landowner_ids(self):
        """Compute filtered landowner IDs based on village"""
        for record in self:
            if record.village_id:
                # Find all surveys for this village
                surveys = self.env['bhu.survey'].search([('village_id', '=', record.village_id.id)])
                # Get all unique landowners from these surveys
                landowner_ids = surveys.mapped('landowner_ids')
                record.filtered_landowner_ids = landowner_ids
            else:
                record.filtered_landowner_ids = False
    
    @api.depends('village_id', 'landowner_id')
    def _compute_filtered_survey_ids(self):
        """Compute filtered survey IDs based on village and landowner"""
        for record in self:
            if record.village_id and record.landowner_id:
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('landowner_ids', 'in', [record.landowner_id.id])
                ])
                record.filtered_survey_ids = surveys
            elif record.village_id:
                surveys = self.env['bhu.survey'].search([('village_id', '=', record.village_id.id)])
                record.filtered_survey_ids = surveys
            else:
                record.filtered_survey_ids = False
    
    # Survey Details (read-only, populated from selected survey)
    survey_khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', readonly=True, compute='_compute_survey_details', store=False)
    survey_total_area = fields.Float(string='Total Area / कुल क्षेत्रफल', readonly=True, compute='_compute_survey_details', store=False)
    survey_acquired_area = fields.Float(string='Acquired Area / अर्जन क्षेत्रफल', readonly=True, compute='_compute_survey_details', store=False)
    survey_date = fields.Date(string='Survey Date / सर्वे दिनांक', readonly=True, compute='_compute_survey_details', store=False)
    survey_state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / स्वीकृत'),
        ('locked', 'Locked / लॉक'),
    ], string='Survey Status / सर्वे स्थिति', readonly=True, compute='_compute_survey_details', store=False)
    survey_project_id = fields.Many2one('bhu.project', string='Survey Project', readonly=True, compute='_compute_survey_details', store=False)
    survey_village_id = fields.Many2one('bhu.village', string='Survey Village', readonly=True, compute='_compute_survey_details', store=False)
    survey_department_id = fields.Many2one('bhu.department', string='Survey Department', readonly=True, compute='_compute_survey_details', store=False)
    survey_crop_type = fields.Selection([
        ('single', 'Single Crop / एकल फसल'),
        ('double', 'Double Crop / दोहरी फसल'),
    ], string='Crop Type / फसल का प्रकार', readonly=True, compute='_compute_survey_details', store=False)
    survey_irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई का प्रकार', readonly=True, compute='_compute_survey_details', store=False)
    survey_tree_count = fields.Integer(string='Tree Count / वृक्ष संख्या', readonly=True, compute='_compute_survey_details', store=False)
    survey_tree_development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully developed / पूर्ण विकसित')
    ], string='Tree Development Stage / वृक्ष विकास स्तर', readonly=True, compute='_compute_survey_details', store=False)
    survey_has_house = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has House / घर है', readonly=True, compute='_compute_survey_details', store=False)
    survey_house_type = fields.Selection([
        ('kachcha', 'कच्चा'),
        ('pucca', 'पक्का')
    ], string='House Type / घर का प्रकार', readonly=True, compute='_compute_survey_details', store=False)
    survey_house_area = fields.Float(string='House Area (Sq. Ft.) / घर का क्षेत्रफल', readonly=True, compute='_compute_survey_details', store=False)
    survey_has_well = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Well / कुआं है', readonly=True, compute='_compute_survey_details', store=False)
    survey_well_type = fields.Selection([
        ('kachcha', 'कच्चा'),
        ('pakka', 'पक्का')
    ], string='Well Type / कुएं का प्रकार', readonly=True, compute='_compute_survey_details', store=False)
    survey_has_tubewell = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Tubewell / ट्यूबवेल है', readonly=True, compute='_compute_survey_details', store=False)
    survey_has_pond = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Pond / तालाब है', readonly=True, compute='_compute_survey_details', store=False)
    survey_landowner_ids = fields.Many2many('bhu.landowner', string='Survey Landowners', readonly=True, compute='_compute_survey_details', store=False)
    
    @api.depends('survey_id')
    def _compute_survey_details(self):
        """Compute survey details from selected survey"""
        for record in self:
            if record.survey_id:
                record.survey_khasra_number = record.survey_id.khasra_number
                record.survey_total_area = record.survey_id.total_area
                record.survey_acquired_area = record.survey_id.acquired_area
                record.survey_date = record.survey_id.survey_date
                record.survey_state = record.survey_id.state
                record.survey_project_id = record.survey_id.project_id
                record.survey_village_id = record.survey_id.village_id
                record.survey_department_id = record.survey_id.department_id
                record.survey_crop_type = record.survey_id.crop_type
                record.survey_irrigation_type = record.survey_id.irrigation_type
                record.survey_tree_count = record.survey_id.tree_count
                record.survey_tree_development_stage = record.survey_id.tree_development_stage
                record.survey_has_house = record.survey_id.has_house
                record.survey_house_type = record.survey_id.house_type
                record.survey_house_area = record.survey_id.house_area
                record.survey_has_well = record.survey_id.has_well
                record.survey_well_type = record.survey_id.well_type
                record.survey_has_tubewell = record.survey_id.has_tubewell
                record.survey_has_pond = record.survey_id.has_pond
                record.survey_landowner_ids = record.survey_id.landowner_ids
            else:
                record.survey_khasra_number = False
                record.survey_total_area = 0.0
                record.survey_acquired_area = 0.0
                record.survey_date = False
                record.survey_state = False
                record.survey_project_id = False
                record.survey_village_id = False
                record.survey_department_id = False
                record.survey_crop_type = False
                record.survey_irrigation_type = False
                record.survey_tree_count = 0
                record.survey_tree_development_stage = False
                record.survey_has_house = False
                record.survey_house_type = False
                record.survey_house_area = 0.0
                record.survey_has_well = False
                record.survey_well_type = False
                record.survey_has_tubewell = False
                record.survey_has_pond = False
                record.survey_landowner_ids = False
    
    objection_type = fields.Selection([
        ('area_increase', 'Area Increase / क्षेत्रफल वृद्धि'),
        ('rate_increase', 'Rate Increase / दर वृद्धि'),
        ('boundary_dispute', 'Boundary Dispute / सीमा विवाद'),
        ('ownership_dispute', 'Ownership Dispute / स्वामित्व विवाद'),
        ('compensation_amount', 'Compensation Amount / मुआवजा राशि'),
        ('survey_errors', 'Survey Errors / सर्वे त्रुटियां'),
        ('tree_count_issue', 'Tree Count Issue / वृक्ष संख्या समस्या'),
        ('other', 'Other / अन्य'),
    ], string='Objection Type / आपत्ति प्रकार', required=True, tracking=True, default='other')
    
    # Objection-specific fields
    new_area = fields.Float(string='Expected New Area (Hectares) / अपेक्षित नया क्षेत्रफल (हेक्टेयर)', 
                            digits=(10, 4), tracking=True,
                            help='Enter the new area that the landowner expects')
    new_rate = fields.Float(string='Expected New Rate (per Hectare) / अपेक्षित नई दर (प्रति हेक्टेयर)', 
                           digits=(10, 2), tracking=True,
                           help='Enter the new rate per hectare that the landowner expects')
    other_specific_details = fields.Text(string='Specific Details / विशिष्ट विवरण', tracking=True,
                                        help='Enter specific details for this objection type (e.g., tree count, boundary details, etc.)')
    
    objection_date = fields.Date(string='Objection Date / आपत्ति दिनांक', required=True, tracking=True, default=fields.Date.today)
    objection_details = fields.Text(string='Objection Details / आपत्ति विवरण', required=True, tracking=True)
    
    # Single attachment file
    objection_document = fields.Binary(string='Objection Document / आपत्ति दस्तावेज़')
    objection_document_filename = fields.Char(string='Document Filename / दस्तावेज़ फ़ाइल नाम')
    status = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('received', 'Received / प्राप्त'),
        ('under_review', 'Under Review / समीक्षा के अधीन'),
        ('resolved', 'Resolved / हल'),
        ('rejected', 'Rejected / अस्वीकृत'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    resolution_details = fields.Text(string='Resolution Details / समाधान विवरण', tracking=True)
    resolved_date = fields.Date(string='Resolved Date / समाधान दिनांक', tracking=True)
    
    # Age in days since objection date
    age_days = fields.Integer(string='Age (Days) / आयु (दिन)', compute='_compute_age_days', store=False)
    
    @api.depends('objection_date')
    def _compute_age_days(self):
        """Compute age of objection in days"""
        today = date.today()
        for record in self:
            if record.objection_date:
                delta = today - record.objection_date
                record.age_days = delta.days
            else:
                record.age_days = 0
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate objection reference if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section15_objection', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or 'New'
                        vals['name'] = f'OBJ-{sequence}'
                else:
                    # No project_id, use fallback
                    sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or 'New'
                    vals['name'] = f'OBJ-{sequence}'
        return super().create(vals_list)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        self.village_id = False
        self.landowner_id = False
        self.survey_id = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_id': []}}
    
    @api.onchange('village_id')
    def _onchange_village_id(self):
        """Reset landowner and survey when village changes"""
        self.landowner_id = False
        self.survey_id = False
        # Trigger recomputation of filtered fields
        self._compute_filtered_landowner_ids()
        self._compute_filtered_survey_ids()
        if self.filtered_landowner_ids:
            return {'domain': {'landowner_id': [('id', 'in', self.filtered_landowner_ids.ids)]}}
        return {'domain': {'landowner_id': [('id', 'in', [])]}}
    
    @api.onchange('landowner_id')
    def _onchange_landowner_id(self):
        """Filter surveys by village and landowner when landowner changes"""
        self.survey_id = False
        # Trigger recomputation of filtered_survey_ids
        self._compute_filtered_survey_ids()
        if self.filtered_survey_ids:
            return {'domain': {'survey_id': [('id', 'in', self.filtered_survey_ids.ids)]}}
        return {'domain': {'survey_id': [('id', 'in', [])]}}
    


    def action_resolve(self):
        """Mark objection as resolved"""
        for record in self:
            # Check if resolution_details is empty or only whitespace
            if not record.resolution_details or not record.resolution_details.strip():
                raise ValidationError(_('Please enter resolution details in the "Resolution / समाधान" tab before resolving.'))
            record.status = 'resolved'
            record.resolved_date = fields.Date.today()
            record.message_post(
                body=_('Objection resolved by %s') % self.env.user.name,
                message_type='notification'
            )

