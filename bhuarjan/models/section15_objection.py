# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
            else:
                record.survey_khasra_number = False
                record.survey_total_area = 0.0
                record.survey_acquired_area = 0.0
                record.survey_date = False
                record.survey_state = False
    
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
    objection_document = fields.Binary(string='Objection Document / आपत्ति दस्तावेज', tracking=True, 
                                       help='Upload PDF document related to this objection')
    objection_document_filename = fields.Char(string='Document Filename / दस्तावेज फ़ाइलनाम')
    has_document = fields.Boolean(string='Has Document / दस्तावेज है', compute='_compute_has_document', store=False)
    
    @api.depends('objection_document')
    def _compute_has_document(self):
        """Compute if objection document exists"""
        for record in self:
            record.has_document = bool(record.objection_document)
    status = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('received', 'Received / प्राप्त'),
        ('under_review', 'Under Review / समीक्षा के अधीन'),
        ('resolved', 'Resolved / हल'),
        ('rejected', 'Rejected / अस्वीकृत'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    resolution_details = fields.Text(string='Resolution Details / समाधान विवरण', tracking=True)
    resolved_date = fields.Date(string='Resolved Date / समाधान दिनांक', tracking=True)
    
    @api.model
    def create(self, vals):
        """Generate objection reference if not provided"""
        if vals.get('name', 'New') == 'New':
            sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or 'New'
            vals['name'] = f'OBJ-{sequence}'
        return super(Section15Objection, self).create(vals)

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
            if not record.resolution_details:
                raise ValidationError(_('Please enter resolution details before resolving.'))
            record.status = 'resolved'
            record.resolved_date = fields.Date.today()
            record.message_post(
                body=_('Objection resolved by %s') % self.env.user.name,
                message_type='notification'
            )

