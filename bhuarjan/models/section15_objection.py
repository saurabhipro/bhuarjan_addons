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
    
    # Single survey (khasra) selection - multiple objections can be created for the same survey
    survey_id = fields.Many2one('bhu.survey', string='Survey (Khasra) / सर्वे (खसरा)', tracking=True,
                                help='Select a khasra from the selected village. Multiple objections can be created for the same khasra to track different changes (landowner added/removed, area decreased).')
    
    # Available surveys for selection (computed based on village)
    available_survey_ids = fields.Many2many('bhu.survey', string='Available Surveys', compute='_compute_available_survey_ids', store=False)
    
    # Landowners from selected surveys (can be removed or added)
    resolution_landowner_ids = fields.Many2many('bhu.landowner', 
                                                'section15_objection_landowner_rel',
                                                'objection_id', 'landowner_id',
                                                string='Landowners (After Resolution) / भूमिस्वामी (समाधान के बाद)', 
                                                tracking=True,
                                                help='Landowners after resolution. You can add or remove landowners. Changes are tracked in the survey.')
    
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
        """Compute available survey IDs based on village - show all khasras from that village"""
        for record in self:
            if record.village_id:
                # Find all surveys (khasras) for this village
                # Multiple objections can be created for the same survey
                # Order by khasra_number descending
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('state', 'in', ['draft', 'submitted', 'approved'])  # Only show valid surveys
                ], order='khasra_number desc')
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
    ], string='Objection Type / आपत्ति प्रकार', required=False, tracking=True)
    
    objection_date = fields.Date(string='Objection Date / आपत्ति दिनांक', required=True, tracking=True, default=fields.Date.today)
    objection_details = fields.Text(string='Objection Details / आपत्ति विवरण', required=False, tracking=True)
    
    # Single attachment file
    objection_document = fields.Binary(string='Objection Document / आपत्ति दस्तावेज़')
    objection_document_filename = fields.Char(string='Objection Document Filename / आपत्ति दस्तावेज़ फ़ाइल नाम')
    
    # Resolution document
    resolution_document = fields.Binary(string='Resolution Document / समाधान दस्तावेज़')
    resolution_document_filename = fields.Char(string='Resolution Document Filename / समाधान दस्तावेज़ फ़ाइल नाम')
    
    # Extend workflow state with "rejected" without overriding the base workflow selection
    state = fields.Selection(selection_add=[('rejected', 'Rejected')], tracking=True)
    
    resolution_details = fields.Text(string='Resolution Details / समाधान विवरण', required=False, tracking=True)
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
    
    @api.onchange('resolution_landowner_ids')
    def _onchange_resolution_landowner_ids(self):
        """Auto-generate objection number when landowners are changed"""
        if self.survey_id and self.resolution_landowner_ids and self.name == 'New':
            # Check if landowners actually changed
            if set(self.resolution_landowner_ids.ids) != set(self.original_landowner_ids.ids):
                # Auto-generate objection number
                if self.project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section15_objection', self.project_id.id, village_id=self.village_id.id if self.village_id else None
                    )
                    if sequence_number:
                        self.name = sequence_number
                    else:
                        sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or str(self._origin.id or 'NEW')
                        self.name = f'OBJ-{sequence}'
                
                # Show warning message
                return {
                    'warning': {
                        'title': _('Objection Created / आपत्ति बनाई गई'),
                        'message': _('Landowner changes detected. Objection %s has been created automatically. Please save to confirm.') % self.name +
                                 '\n\n' + _('भूमिस्वामी परिवर्तन का पता चला। आपत्ति %s स्वचालित रूप से बनाई गई है। पुष्टि करने के लिए कृपया सहेजें।') % self.name
                    }
                }
    
    @api.onchange('resolution_khasra_ids')
    def _onchange_resolution_khasra_ids(self):
        """Auto-generate objection number when area is changed"""
        if self.survey_id and self.resolution_khasra_ids and self.name == 'New':
            # Check if any area was actually changed
            for khasra in self.resolution_khasra_ids:
                if khasra.resolved_acquired_area and khasra.resolved_acquired_area != khasra.original_acquired_area:
                    # Auto-generate objection number
                    if self.project_id:
                        sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                            'section15_objection', self.project_id.id, village_id=self.village_id.id if self.village_id else None
                        )
                        if sequence_number:
                            self.name = sequence_number
                        else:
                            sequence = self.env['ir.sequence'].next_by_code('bhu.section15.objection') or str(self._origin.id or 'NEW')
                            self.name = f'OBJ-{sequence}'
                    
                    # Show warning message
                    return {
                        'warning': {
                            'title': _('Objection Created / आपत्ति बनाई गई'),
                            'message': _('Area changes detected. Objection %s has been created automatically. Please save to confirm.') % self.name +
                                     '\n\n' + _('क्षेत्रफल परिवर्तन का पता चला। आपत्ति %s स्वचालित रूप से बनाई गई है। पुष्टि करने के लिए कृपया सहेजें।') % self.name
                        }
                    }
                    break
    
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
        # Also link this objection to the survey
        for record in records:
            if record.survey_id:
                # Link objection to survey (Many2many)
                record.survey_id.section15_objection_ids = [(4, record.id)]
                
                if record.objection_type == 'area_decrease' and not record.resolution_khasra_ids:
                    record.resolution_khasra_ids = [(0, 0, {
                        'survey_id': record.survey_id.id,
                        'original_acquired_area': record.survey_id.acquired_area,
                        'resolved_acquired_area': record.survey_id.acquired_area,
                    })]
            
            # Validate that changes were made
            record._validate_objection_changes()
        
        return records
    
    def _validate_objection_changes(self):
        """Validate that actual changes were made before saving objection"""
        for record in self:
            if not record.survey_id:
                continue
            
            # Check if landowners changed
            landowners_changed = False
            if record.resolution_landowner_ids and record.original_landowner_ids:
                landowners_changed = set(record.resolution_landowner_ids.ids) != set(record.original_landowner_ids.ids)
            
            # Check if area changed
            area_changed = False
            if record.resolution_khasra_ids:
                for khasra in record.resolution_khasra_ids:
                    if khasra.resolved_acquired_area and khasra.original_acquired_area:
                        if khasra.resolved_acquired_area != khasra.original_acquired_area:
                            area_changed = True
                            break
            
            # If neither changed, raise error
            if not landowners_changed and not area_changed:
                raise ValidationError(_(
                    'No changes detected! Cannot save objection without any changes to landowners or khasra area.\n\n'
                    'कोई परिवर्तन नहीं मिला! भूमिस्वामी या खसरा क्षेत्रफल में कोई परिवर्तन किए बिना आपत्ति सहेजी नहीं जा सकती।'
                ))
    
    def write(self, vals):
        """Override write to update survey when objection is saved"""
        # Validate changes before write (only for resolution fields)
        if 'resolution_landowner_ids' in vals or 'resolution_khasra_ids' in vals:
            # After write, validate changes
            result = super().write(vals)
            self._validate_objection_changes()
        else:
            result = super().write(vals)
        
        # Update survey's landowners when resolution_landowner_ids changes
        if 'resolution_landowner_ids' in vals:
            for record in self:
                if record.survey_id and record.resolution_landowner_ids:
                    # Update survey's landowners to match objection resolution
                    record.survey_id.write({
                        'landowner_ids': [(6, 0, record.resolution_landowner_ids.ids)]
                    })
        
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
            self.resolution_khasra_ids = [(5, 0, 0)]
            return
        
        # Compute original landowners
        all_landowners = self.survey_id.landowner_ids
        self.original_landowner_ids = all_landowners
        # Initialize resolution_landowner_ids with original if not set
        if not self.resolution_landowner_ids and all_landowners:
            self.resolution_landowner_ids = all_landowners
        
        # Initialize or update resolution khasra record
        if self.resolution_khasra_ids and len(self.resolution_khasra_ids) > 0:
            # Update existing record
            existing = self.resolution_khasra_ids[0]
            if existing.id:
                existing.write({
                    'survey_id': self.survey_id.id,
                    'original_acquired_area': self.survey_id.acquired_area,
                })
                if existing.resolved_acquired_area > self.survey_id.acquired_area:
                    existing.write({'resolved_acquired_area': self.survey_id.acquired_area})
            else:
                existing.survey_id = self.survey_id.id
                existing.original_acquired_area = self.survey_id.acquired_area
                if existing.resolved_acquired_area > self.survey_id.acquired_area:
                    existing.resolved_acquired_area = self.survey_id.acquired_area
        else:
            # Create new record
            if self.survey_id.id:
                self.resolution_khasra_ids = [(0, 0, {
                    'survey_id': self.survey_id.id,
                    'original_acquired_area': self.survey_id.acquired_area,
                    'resolved_acquired_area': self.survey_id.acquired_area,
                })]
    
    @api.constrains('resolution_landowner_ids')
    def _check_resolution_landowners(self):
        """Ensure at least one landowner remains"""
        for record in self:
            # Ensure at least one landowner remains
            if not record.resolution_landowner_ids:
                raise ValidationError(_('At least one landowner must remain. You cannot remove all landowners.'))
    
    @api.constrains('resolution_khasra_ids')
    def _check_resolution_areas(self):
        """Ensure resolved areas are not greater than original areas - SDM can only decrease, not increase"""
        for record in self:
            for khasra in record.resolution_khasra_ids:
                if khasra.original_acquired_area and khasra.resolved_acquired_area:
                    if khasra.resolved_acquired_area > khasra.original_acquired_area:
                        raise ValidationError(_('Resolved acquired area (%.4f hectares) cannot be greater than original area (%.4f hectares) for khasra %s. You can only decrease the area, not increase it.') % 
                                            (khasra.resolved_acquired_area, khasra.original_acquired_area, khasra.survey_id.khasra_number or khasra.khasra_number or ''))
    
    def action_approve(self):
        """Approve objection (SDM action)"""
        self.ensure_one()
        
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can approve.'))
        
        # Resolution details is optional, no validation needed
        
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
    
    def set_state_approved(self):
        """Set state to approved when clicking on approved status button"""
        self.ensure_one()
        # Allow going to approved from draft state
        if self.state == 'draft':
            # Check if user is SDM
            if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                    self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
                raise ValidationError(_('Only SDM can approve.'))
            # Resolution details is optional, no validation needed
            # Set resolved date
            self.resolved_date = fields.Date.today()
            self.state = 'approved'
            self.message_post(body=_('Status changed to Approved by %s') % self.env.user.name)
        elif self.state == 'approved':
            # Already in approved state
            pass
        else:
            raise ValidationError(_('Cannot change status to Approved from current state. Only draft records can be approved.'))
    
    def set_state_rejected(self):
        """Set state to rejected when clicking on rejected status button"""
        self.ensure_one()
        # Allow going to rejected from draft state
        if self.state == 'draft':
            # Check if user is SDM
            if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                    self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
                raise ValidationError(_('Only SDM can reject.'))
            self.state = 'rejected'
            self.message_post(body=_('Status changed to Rejected by %s') % self.env.user.name)
        elif self.state == 'rejected':
            # Already in rejected state
            pass
        else:
            raise ValidationError(_('Cannot change status to Rejected from current state. Only draft records can be rejected.'))
    
    def _validate_state_to_approved(self):
        """Validate transition to approved state"""
        self.ensure_one()
        # Allow going to approved from draft state
        if self.state != 'draft':
            raise ValidationError(_('Cannot change status to Approved from current state. Only draft records can be approved.'))
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can approve.'))
        # Resolution details is optional, no validation needed
    
    def _validate_state_to_rejected(self):
        """Validate transition to rejected state"""
        self.ensure_one()
        # Allow going to rejected from draft state
        if self.state != 'draft':
            raise ValidationError(_('Cannot change status to Rejected from current state. Only draft records can be rejected.'))
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can reject.'))
    
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
    
    def unlink(self):
        """Remove objection from survey when deleted"""
        # Store survey_ids and objection_ids before deletion
        survey_objection_map = {}
        for record in self:
            if record.survey_id:
                if record.survey_id.id not in survey_objection_map:
                    survey_objection_map[record.survey_id.id] = []
                survey_objection_map[record.survey_id.id].append(record.id)
        
        result = super().unlink()
        
        # Remove from survey's objection list
        for survey_id, objection_ids in survey_objection_map.items():
            survey = self.env['bhu.survey'].browse(survey_id)
            if survey.exists():
                for objection_id in objection_ids:
                    survey.section15_objection_ids = [(3, objection_id)]
        
        return result


class Section15ObjectionKhasra(models.Model):
    """Model to track resolution changes per khasra (survey)"""
    _name = 'bhu.section15.objection.khasra'
    _description = 'Section 15 Objection Khasra Resolution'
    
    objection_id = fields.Many2one('bhu.section15.objection', string='Objection / आपत्ति', required=True, ondelete='cascade')
    survey_id = fields.Many2one('bhu.survey', string='Survey (Khasra) / सर्वे (खसरा)', required=True, 
                               ondelete='restrict')
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', related='survey_id.khasra_number', readonly=True, store=True)
    original_acquired_area = fields.Float(string='Original Acquired Area (Hectares) / मूल अर्जन क्षेत्रफल (हेक्टेयर)', 
                                          digits=(10, 4), required=True, readonly=True)
    resolved_acquired_area = fields.Float(string='Resolved Acquired Area (Hectares) / समाधान अर्जन क्षेत्रफल (हेक्टेयर)', 
                                         digits=(10, 4), required=True,
                                         help='Enter the resolved acquired area. Must be less than or equal to original area.')
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        # Set objection_id from context if available
        if 'default_objection_id' in self.env.context:
            objection_id = self.env.context.get('default_objection_id')
            if objection_id and 'objection_id' in fields_list:
                res['objection_id'] = objection_id
        
        # Try to get survey_id from context
        survey_id = self.env.context.get('default_survey_id')
        
        # If not in context, try to get from objection_id
        if not survey_id and 'default_objection_id' in self.env.context:
            objection_id = self.env.context.get('default_objection_id')
            if objection_id:
                objection = self.env['bhu.section15.objection'].browse(objection_id)
                if objection.exists() and objection.survey_id:
                    survey_id = objection.survey_id.id
        
        if survey_id:
            survey = self.env['bhu.survey'].browse(survey_id)
            if survey.exists():
                if 'survey_id' in fields_list:
                    res['survey_id'] = survey_id
                if 'original_acquired_area' in fields_list:
                    res['original_acquired_area'] = survey.acquired_area
                if 'resolved_acquired_area' in fields_list:
                    res['resolved_acquired_area'] = survey.acquired_area
        
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure survey_id is set from objection if not provided"""
        # Set survey_id in vals_list before creation
        for vals in vals_list:
            if not vals.get('survey_id') and vals.get('objection_id'):
                objection = self.env['bhu.section15.objection'].browse(vals['objection_id'])
                if objection.exists() and objection.survey_id:
                    vals['survey_id'] = objection.survey_id.id
                    # Also set areas if not set
                    if not vals.get('original_acquired_area'):
                        vals['original_acquired_area'] = objection.survey_id.acquired_area
                    if not vals.get('resolved_acquired_area'):
                        vals['resolved_acquired_area'] = objection.survey_id.acquired_area
        
        records = super().create(vals_list)
        
        # After creation, ensure survey_id is set for any records that still don't have it
        for record in records:
            if not record.survey_id and record.objection_id and record.objection_id.survey_id:
                record.write({
                    'survey_id': record.objection_id.survey_id.id,
                    'original_acquired_area': record.objection_id.survey_id.acquired_area,
                    'resolved_acquired_area': record.objection_id.survey_id.acquired_area,
                })
            
            # Update survey's acquired_area when resolved_acquired_area is set
            if record.survey_id and record.resolved_acquired_area:
                # Ensure resolved area is valid (not greater than original)
                if record.original_acquired_area and record.resolved_acquired_area <= record.original_acquired_area:
                    # Update the survey's acquired_area to match the resolved_acquired_area
                    record.survey_id.write({'acquired_area': record.resolved_acquired_area})
        
        return records
    
    def write(self, vals):
        """Ensure survey_id is set from objection if not provided, and update survey's acquired_area when resolved_acquired_area changes"""
        # Track which records need survey update
        records_to_update_survey = []
        resolved_area_value = None
        
        # Check if resolved_acquired_area is being updated
        if 'resolved_acquired_area' in vals:
            resolved_area_value = vals['resolved_acquired_area']
            records_to_update_survey = self
        
        result = super().write(vals)
        
        # After write, ensure survey_id is set for any records that don't have it
        for record in self:
            if not record.survey_id and record.objection_id and record.objection_id.survey_id:
                record.write({
                    'survey_id': record.objection_id.survey_id.id,
                    'original_acquired_area': record.objection_id.survey_id.acquired_area,
                })
                if not record.resolved_acquired_area or record.resolved_acquired_area > record.objection_id.survey_id.acquired_area:
                    record.write({'resolved_acquired_area': record.objection_id.survey_id.acquired_area})
        
        # Update survey's acquired_area when resolved_acquired_area is changed
        for record in records_to_update_survey:
            if record.survey_id and record.resolved_acquired_area:
                # Ensure resolved area is valid (not greater than original)
                if record.original_acquired_area and record.resolved_acquired_area <= record.original_acquired_area:
                    # Update the survey's acquired_area to match the resolved_acquired_area
                    record.survey_id.write({'acquired_area': record.resolved_acquired_area})
        
        return result
    
    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        """Update area fields when survey changes - ensure resolved area doesn't exceed original"""
        if self.survey_id:
            self.original_acquired_area = self.survey_id.acquired_area
            # If resolved area is greater than original, set it to original (can only decrease)
            if not self.resolved_acquired_area or self.resolved_acquired_area > self.survey_id.acquired_area:
                self.resolved_acquired_area = self.survey_id.acquired_area
    
    @api.onchange('resolved_acquired_area')
    def _onchange_resolved_acquired_area(self):
        """Ensure resolved area doesn't exceed original area - SDM can only decrease, not increase"""
        if self.original_acquired_area and self.resolved_acquired_area:
            if self.resolved_acquired_area > self.original_acquired_area:
                # Reset to original if user tries to increase
                self.resolved_acquired_area = self.original_acquired_area
                return {
                    'warning': {
                        'title': _('Area Cannot Be Increased'),
                        'message': _('You can only decrease the acquired area, not increase it. The resolved area has been set to the original area (%.4f hectares).') % self.original_acquired_area
                    }
                }
    
    @api.constrains('resolved_acquired_area', 'original_acquired_area')
    def _check_area_decrease(self):
        """Ensure resolved area is not greater than original - SDM can only decrease, not increase"""
        for record in self:
            if record.original_acquired_area and record.resolved_acquired_area:
                if record.resolved_acquired_area > record.original_acquired_area:
                    raise ValidationError(_('Resolved acquired area (%.4f hectares) cannot be greater than original area (%.4f hectares) for khasra %s. You can only decrease the area, not increase it.') % 
                                        (record.resolved_acquired_area, record.original_acquired_area, record.khasra_number or record.survey_id.khasra_number or ''))

