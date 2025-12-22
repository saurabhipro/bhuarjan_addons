# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import json

class Section15Objection(models.Model):
    _name = 'bhu.section15.objection'
    _description = 'Section 15 Objections'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.process.workflow.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Objection Reference / आपत्ति संदर्भ', required=True, tracking=True, default='New', readonly=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # Single survey (khasra) selection
    survey_id = fields.Many2one('bhu.survey', string='Survey (Khasra) / सर्वे (खसरा)', tracking=True,
                                help='Select a survey (khasra) from the selected village')
    
    # Available surveys for selection (computed based on village)
    available_survey_ids = fields.Many2many('bhu.survey', string='Available Surveys', compute='_compute_available_survey_ids', store=False)
    
    # Landowners from selected surveys (can be removed, cannot add new)
    resolution_landowner_ids = fields.Many2many('bhu.landowner', 
                                                'section15_objection_landowner_rel',
                                                'objection_id', 'landowner_id',
                                                string='Landowners (After Resolution) / भूमिस्वामी (समाधान के बाद)', 
                                                tracking=True,
                                                help='Landowners after resolution. You can remove landowners but cannot add new ones.')
    
    # Original landowners from surveys (readonly, for comparison)
    original_landowner_ids = fields.Many2many('bhu.landowner', 
                                             'section15_objection_original_landowner_rel',
                                             'objection_id', 'landowner_id',
                                             string='Original Landowners / मूल भूमिस्वामी', 
                                             compute='_compute_original_landowner_ids', 
                                             store=False, readonly=True)
    
    # Resolution changes per khasra (One2many to track area decreases per survey)
    resolution_khasra_ids = fields.One2many('bhu.section15.objection.khasra', 'objection_id',
                                            string='Khasra Resolution Changes / खसरा समाधान परिवर्तन',
                                            tracking=True,
                                            help='Track area decreases per khasra')
    
    @api.depends('village_id')
    def _compute_available_survey_ids(self):
        """Compute available survey IDs based on village"""
        for record in self:
            if record.village_id:
                # Find all surveys for this village
                surveys = self.env['bhu.survey'].search([('village_id', '=', record.village_id.id)])
                record.available_survey_ids = surveys
            else:
                record.available_survey_ids = False
    
    @api.depends('survey_id')
    def _compute_original_landowner_ids(self):
        """Compute original landowners from selected survey"""
        for record in self:
            if record.survey_id:
                # Get all landowners from selected survey
                all_landowners = record.survey_id.landowner_ids
                record.original_landowner_ids = all_landowners
                # Initialize resolution_landowner_ids with original if not set
                if not record.resolution_landowner_ids and all_landowners:
                    record.resolution_landowner_ids = all_landowners
            else:
                record.original_landowner_ids = False
                record.resolution_landowner_ids = False
    
    
    objection_type = fields.Selection([
        ('area_decrease', 'Area Decrease / क्षेत्रफल कमी'),
        ('remove_landowners', 'Remove Landowners / भूमिस्वामी हटाना'),
    ], string='Objection Type / आपत्ति प्रकार', required=True, tracking=True, default='area_decrease')
    
    objection_date = fields.Date(string='Objection Date / आपत्ति दिनांक', required=True, tracking=True, default=fields.Date.today)
    objection_details = fields.Text(string='Objection Details / आपत्ति विवरण', required=True, tracking=True)
    
    # Single attachment file
    objection_document = fields.Binary(string='Objection Document / आपत्ति दस्तावेज़')
    objection_document_filename = fields.Char(string='Document Filename / दस्तावेज़ फ़ाइल नाम')
    # Override state field for Section 15 - simpler workflow: Draft, Approved, Rejected
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
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
        records = super().create(vals_list)
        
        # Initialize resolution khasra if survey_id is set and objection type is area_decrease
        for record in records:
            if record.survey_id and record.objection_type == 'area_decrease' and not record.resolution_khasra_ids:
                record.resolution_khasra_ids = [(0, 0, {
                    'survey_id': record.survey_id.id,
                    'original_acquired_area': record.survey_id.acquired_area,
                    'resolved_acquired_area': record.survey_id.acquired_area,
                })]
        return records
    
    def write(self, vals):
        """Override write to ensure resolution_khasra_ids have survey_id set"""
        result = super().write(vals)
        
        # If survey_id or objection_type changed, update resolution_khasra_ids
        if 'survey_id' in vals or 'objection_type' in vals:
            for record in self:
                if record.objection_type == 'area_decrease' and record.survey_id:
                    # Ensure resolution_khasra_ids exists and has survey_id
                    if record.resolution_khasra_ids:
                        for khasra in record.resolution_khasra_ids:
                            if not khasra.survey_id:
                                khasra.write({
                                    'survey_id': record.survey_id.id,
                                    'original_acquired_area': record.survey_id.acquired_area,
                                })
                                if khasra.resolved_acquired_area > record.survey_id.acquired_area:
                                    khasra.write({'resolved_acquired_area': record.survey_id.acquired_area})
                    elif record.survey_id:
                        # Create if doesn't exist
                        record.resolution_khasra_ids = [(0, 0, {
                            'survey_id': record.survey_id.id,
                            'original_acquired_area': record.survey_id.acquired_area,
                            'resolved_acquired_area': record.survey_id.acquired_area,
                        })]
                elif record.objection_type == 'remove_landowners':
                    # Clear resolution_khasra_ids for remove_landowners type
                    record.resolution_khasra_ids = [(5, 0, 0)]
        
        return result

    

    village_domain = fields.Char()
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([])   # empty domain
                rec.village_id = False
    
    @api.onchange('village_id')
    def _onchange_village_id(self):
        """Reset survey when village changes"""
        self.survey_id = False
        self.resolution_landowner_ids = False
        self.resolution_khasra_ids = False
        # Trigger recomputation
        self._compute_available_survey_ids()
    
    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        """Update original landowners and initialize resolution data when survey changes"""
        if not self.survey_id:
            self.resolution_landowner_ids = False
            # Clear resolution khasra records using One2many command
            self.resolution_khasra_ids = [(5, 0, 0)]
            return
        
        # Compute original landowners
        all_landowners = self.survey_id.landowner_ids
        self.original_landowner_ids = all_landowners
        # Initialize resolution_landowner_ids with original if not set
        if not self.resolution_landowner_ids and all_landowners:
            self.resolution_landowner_ids = all_landowners
        
        # Initialize or update resolution khasra record (only for area_decrease objection type)
        if self.objection_type == 'area_decrease':
            if self.resolution_khasra_ids and len(self.resolution_khasra_ids) > 0:
                # Update existing record
                existing = self.resolution_khasra_ids[0]
                # Use write to update the record properly
                if existing.id:
                    existing.write({
                        'survey_id': self.survey_id.id,
                        'original_acquired_area': self.survey_id.acquired_area,
                    })
                    if existing.resolved_acquired_area > self.survey_id.acquired_area:
                        existing.write({'resolved_acquired_area': self.survey_id.acquired_area})
                else:
                    # New record, update in place
                    existing.survey_id = self.survey_id.id
                    existing.original_acquired_area = self.survey_id.acquired_area
                    if existing.resolved_acquired_area > self.survey_id.acquired_area:
                        existing.resolved_acquired_area = self.survey_id.acquired_area
            else:
                # Create new record - ensure survey_id is set
                if self.survey_id.id:
                    self.resolution_khasra_ids = [(0, 0, {
                        'survey_id': self.survey_id.id,
                        'original_acquired_area': self.survey_id.acquired_area,
                        'resolved_acquired_area': self.survey_id.acquired_area,
                    })]
        else:
            # Clear resolution khasra records for other objection types
            self.resolution_khasra_ids = [(5, 0, 0)]
    
    @api.onchange('objection_type')
    def _onchange_objection_type(self):
        """Clear or initialize resolution data when objection type changes"""
        if self.objection_type == 'area_decrease':
            # For area decrease, ensure resolution khasra is initialized if survey_id exists
            if self.survey_id and not self.resolution_khasra_ids:
                self._onchange_survey_id()
        elif self.objection_type == 'remove_landowners':
            # For remove landowners, clear resolution khasra
            self.resolution_khasra_ids = [(5, 0, 0)]
    
    @api.constrains('resolution_landowner_ids')
    def _check_resolution_landowners(self):
        """Ensure resolution landowners are subset of original landowners and at least one remains"""
        for record in self:
            if record.resolution_landowner_ids and record.original_landowner_ids:
                removed = record.original_landowner_ids - record.resolution_landowner_ids
                added = record.resolution_landowner_ids - record.original_landowner_ids
                if added:
                    raise ValidationError(_('You cannot add new landowners. You can only remove existing landowners.'))
                # Ensure at least one landowner remains
                if not record.resolution_landowner_ids:
                    raise ValidationError(_('At least one landowner must remain. You cannot remove all landowners.'))
    
    @api.constrains('resolution_khasra_ids')
    def _check_resolution_areas(self):
        """Ensure resolved areas are not greater than original areas"""
        for record in self:
            for khasra in record.resolution_khasra_ids:
                if khasra.resolved_acquired_area > khasra.original_acquired_area:
                    raise ValidationError(_('Resolved acquired area (%.4f) cannot be greater than original area (%.4f) for khasra %s.') % 
                                        (khasra.resolved_acquired_area, khasra.original_acquired_area, khasra.survey_id.khasra_number or ''))
    
    def action_approve(self):
        """Approve objection (SDM action)"""
        self.ensure_one()
        
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can approve.'))
        
        # Validate that resolution details exist
        if not self.resolution_details:
            raise ValidationError(_('Please provide resolution details before approving.'))
        
        # Validate state is draft
        if self.state != 'draft':
            raise ValidationError(_('Only draft records can be approved.'))
        
        # Set resolved date
        self.resolved_date = fields.Date.today()
        self.state = 'approved'
        self.message_post(body=_('Approved by %s') % self.env.user.name)
    
    def action_reject(self):
        """Reject objection (SDM action)"""
        self.ensure_one()
        
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can reject.'))
        
        # Validate state is draft
        if self.state != 'draft':
            raise ValidationError(_('Only draft records can be rejected.'))
        
        self.state = 'rejected'
        self.message_post(body=_('Rejected by %s') % self.env.user.name)
    
    def action_download_unsigned_file(self):
        """Download objection document if available"""
        self.ensure_one()
        if not self.objection_document:
            raise ValidationError(_('No objection document available to download.'))
        filename = self.objection_document_filename or f'objection_{self.name}.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/objection_document/{filename}?download=true',
            'target': 'self',
        }
    
    def get_resolution_changes_summary(self):
        """Get summary of resolution changes for report"""
        self.ensure_one()
        changes = []
        
        # Check for removed landowners
        if self.original_landowner_ids and self.resolution_landowner_ids:
            removed = self.original_landowner_ids - self.resolution_landowner_ids
            if removed:
                removed_names = ', '.join(removed.mapped('name'))
                changes.append({
                    'type': 'landowner_removed',
                    'description': f'Removed landowners: {removed_names}',
                    'hindi_description': f'हटाए गए भूमिस्वामी: {removed_names}'
                })
        
        # Check for area decreases
        for khasra in self.resolution_khasra_ids:
            if khasra.resolved_acquired_area < khasra.original_acquired_area:
                decrease = khasra.original_acquired_area - khasra.resolved_acquired_area
                changes.append({
                    'type': 'area_decreased',
                    'khasra': khasra.survey_id.khasra_number or '',
                    'original_area': khasra.original_acquired_area,
                    'resolved_area': khasra.resolved_acquired_area,
                    'decrease': decrease,
                    'description': f'Khasra {khasra.survey_id.khasra_number}: Area decreased from {khasra.original_acquired_area:.4f} to {khasra.resolved_acquired_area:.4f} hectares',
                    'hindi_description': f'खसरा {khasra.survey_id.khasra_number}: क्षेत्रफल {khasra.original_acquired_area:.4f} से {khasra.resolved_acquired_area:.4f} हेक्टेयर तक कम किया गया'
                })
        
        return changes


class Section15ObjectionKhasra(models.Model):
    """Model to track resolution changes per khasra (survey)"""
    _name = 'bhu.section15.objection.khasra'
    _description = 'Section 15 Objection Khasra Resolution'
    
    objection_id = fields.Many2one('bhu.section15.objection', string='Objection / आपत्ति', required=True, ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey (Khasra) / सर्वे (खसरा)', required=True)
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', related='survey_id.khasra_number', readonly=True, store=True)
    original_acquired_area = fields.Float(string='Original Acquired Area (Hectares) / मूल अर्जन क्षेत्रफल (हेक्टेयर)', 
                                          digits=(10, 4), required=True, readonly=True)
    resolved_acquired_area = fields.Float(string='Resolved Acquired Area (Hectares) / समाधान अर्जन क्षेत्रफल (हेक्टेयर)', 
                                         digits=(10, 4), required=True,
                                         help='Enter the resolved acquired area. Must be less than or equal to original area.')
    
    @api.constrains('resolved_acquired_area', 'original_acquired_area')
    def _check_area_decrease(self):
        """Ensure resolved area is not greater than original"""
        for record in self:
            if record.resolved_acquired_area > record.original_acquired_area:
                raise ValidationError(_('Resolved acquired area (%.4f) cannot be greater than original area (%.4f) for khasra %s.') % 
                                    (record.resolved_acquired_area, record.original_acquired_area, record.khasra_number or ''))

