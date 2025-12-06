# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid

class ExpertCommitteeReport(models.Model):
    _name = 'bhu.expert.committee.report'
    _description = 'Expert Committee Report / विशेषज्ञ समिति रिपोर्ट'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.process.workflow.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Report Name / रिपोर्ट का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, ondelete='cascade',
                                  default=lambda self: self._default_project_id(), tracking=True)
    requiring_body_id = fields.Many2one('bhu.department', string='Requiring Body / अपेक्षक निकाय', required=True, tracking=True,
                                       help='Select the requiring body/department', related="project_id.department_id")
    village_ids = fields.Many2many('bhu.village', string='Affected Villages / प्रभावित ग्राम', tracking=True,
                                   help='Select affected villages for this report')
    
    # Computed fields from Form 10 surveys
    total_khasras_count = fields.Integer(string='Total Khasras Count / कुल खसरा संख्या',
                                         compute='_compute_project_statistics', store=False)
    total_area_acquired = fields.Float(string='Total Area Acquired (Hectares) / कुल अर्जित क्षेत्रफल (हेक्टेयर)',
                                       compute='_compute_project_statistics', store=False,
                                       digits=(16, 4))
    
    # Project villages for reference (read-only)
    project_village_ids = fields.Many2many('bhu.village', 
                                           string='Project Villages / परियोजना ग्राम',
                                           compute='_compute_project_villages', 
                                           store=False,
                                           help='Villages mapped to the selected project (read-only for reference)')
    
    # Expert Committee Team Members - 4 Sections
    # (क) Non-Government Social Scientist
    non_govt_social_scientist_ids = fields.Many2many('bhu.sia.team.member', 
                                                     'expert_committee_non_govt_social_scientist_rel',
                                                     'expert_committee_id', 'member_id',
                                                     string='Non-Government Social Scientist / गैर शासकीय सामाजिक वैज्ञानिक',
                                                     tracking=True)
    
    # (ख) Representatives of Local Bodies
    local_bodies_representative_ids = fields.Many2many('bhu.sia.team.member',
                                                       'expert_committee_local_bodies_rep_rel',
                                                       'expert_committee_id', 'member_id',
                                                       string='Representatives of Local Bodies / ग्राम पंचायत या नगरीय निकाय के प्रतिनिधि',
                                                       tracking=True)
    
    # (ग) Resettlement Expert
    resettlement_expert_ids = fields.Many2many('bhu.sia.team.member',
                                                'expert_committee_resettlement_expert_rel',
                                                'expert_committee_id', 'member_id',
                                                string='Resettlement Expert / पुनर्व्यवस्थापन संबंधी विशेषज्ञ',
                                                tracking=True)
    
    # (घ) Technical Expert on Project Related Subject
    technical_expert_ids = fields.Many2many('bhu.sia.team.member',
                                            'expert_committee_technical_expert_rel',
                                            'expert_committee_id', 'member_id',
                                            string='Technical Expert / परियोजना से संबंधित विषय का तकनीकि विशेषज्ञ',
                                            tracking=True)
    
    _sql_constraints = [
        ('project_unique', 'UNIQUE(project_id)', 'Only one Expert Committee Report is allowed per project.')
    ]
    
    @api.depends('project_id', 'project_id.village_ids', 'village_ids')
    def _compute_project_villages(self):
        """Compute villages - show selected villages if any, otherwise show all project villages"""
        for record in self:
            if record.village_ids:
                # Show only selected villages
                record.project_village_ids = record.village_ids
            elif record.project_id and record.project_id.village_ids:
                # If no villages selected, show all project villages
                record.project_village_ids = record.project_id.village_ids
            else:
                record.project_village_ids = False
    
    @api.depends('project_id', 'village_ids')
    def _compute_project_statistics(self):
        """Compute total khasras count and total area acquired from Form 10 surveys"""
        for record in self:
            if record.project_id:
                # If specific villages are selected, use those; otherwise use all project villages
                village_ids = record.village_ids.ids if record.village_ids else record.project_id.village_ids.ids
                
                if village_ids:
                    # Get all surveys for selected villages in this project
                    surveys = self.env['bhu.survey'].search([
                        ('project_id', '=', record.project_id.id),
                        ('village_id', 'in', village_ids),
                        ('khasra_number', '!=', False),
                    ])
                    
                    # Count unique khasra numbers
                    unique_khasras = set(surveys.mapped('khasra_number'))
                    record.total_khasras_count = len(unique_khasras)
                    
                    # Sum acquired area
                    record.total_area_acquired = sum(surveys.mapped('acquired_area'))
                else:
                    record.total_khasras_count = 0
                    record.total_area_acquired = 0.0
            else:
                record.total_khasras_count = 0
                record.total_area_acquired = 0.0
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Auto-populate villages and filter domain based on project selection"""
        # Auto-populate villages with all project villages when project is selected
        if self.project_id and self.project_id.village_ids:
            # Always populate with project villages when project is selected
            self.village_ids = self.project_id.village_ids
        else:
            self.village_ids = False
        
        # Set domain to only show project villages
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_ids': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            return {'domain': {'village_ids': [('id', '=', False)]}}
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists, otherwise use first available project"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        # Fallback to first available project if PROJ01 doesn't exist
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    # Original report file (unsigned)
    report_file = fields.Binary(string='Report File / रिपोर्ट फ़ाइल')
    report_filename = fields.Char(string='File Name / फ़ाइल नाम')
    
    # Signed document fields (similar to Section 4 Notification)
    signed_document_file = fields.Binary(string='Signed Report / हस्ताक्षरित रिपोर्ट')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है', 
                                         compute='_compute_has_signed_document', store=True)
    
    # Signatory information
    signatory_name = fields.Char(string='Signatory Name / हस्ताक्षरकर्ता का नाम', tracking=True)
    signatory_designation = fields.Char(string='Signatory Designation / हस्ताक्षरकर्ता का पद', tracking=True)
    
    # State field is inherited from mixin
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.expert.committee.report') or 'New'
            # Set default project_id if not provided
            if not vals.get('project_id'):
                project_id = self._default_project_id()
                if project_id:
                    vals['project_id'] = project_id
                else:
                    # If no project exists at all, we can't create the record
                    # This should not happen if sample_project_data.xml is loaded first
                    # But if it does, the post-init hook will fix it
                    # For now, we'll try to use any project as a last resort
                    any_project = self.env['bhu.project'].search([], limit=1)
                    if any_project:
                        vals['project_id'] = any_project.id
        return super().create(vals_list)
    
    def action_mark_signed(self):
        """Mark report as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()
    
    # Workflow methods are inherited from mixin
    # Override action_download_unsigned_file to generate PDF report
    def action_download_unsigned_file(self):
        """Generate and download Expert Committee Report PDF (unsigned) - Override mixin"""
        self.ensure_one()
        # TODO: Add report action reference when Expert Committee report template is created
        # For now, return error
        raise ValidationError(_('Expert Committee Report PDF generation is not yet implemented.'))
    
    def action_create_section11_notification(self):
        """Create Section 11 Preliminary Report from this Expert Committee Report - Creates one per village"""
        self.ensure_one()
        
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        
        if not self.village_ids:
            raise ValidationError(_('Please select at least one village first.'))
        
        # Create a separate Section 11 notification for each village
        created_notifications = []
        skipped_villages = []
        
        for village in self.village_ids:
            # Check if Section 11 already exists for this project and village
            existing = self.env['bhu.section11.preliminary.report'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', village.id)
            ], limit=1)
            
            if existing:
                skipped_villages.append(village.name)
                continue
            
            # Create new Section 11 Preliminary Report for this village
            section11 = self.env['bhu.section11.preliminary.report'].create({
                'project_id': self.project_id.id,
                'village_id': village.id,
            })
            created_notifications.append(section11)
        
        if not created_notifications:
            # All villages already have Section 11 notifications
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Section 11 notifications already exist for all selected villages. Skipped: %s') % ', '.join(skipped_villages),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        # Add message to Expert Committee Report
        message = _('Created %d Section 11 Preliminary Report(s) from this Expert Committee Report.') % len(created_notifications)
        if skipped_villages:
            message += _(' Skipped: %s') % ', '.join(skipped_villages)
        self.message_post(body=message)
        
        # Open the created Section 11 reports
        if len(created_notifications) == 1:
            # Open single notification in form view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Section 11 Preliminary Report'),
                'res_model': 'bhu.section11.preliminary.report',
                'res_id': created_notifications[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Open multiple notifications in list view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Section 11 Preliminary Reports'),
                'res_model': 'bhu.section11.preliminary.report',
                'view_mode': 'list,form',
                'domain': [('id', 'in', [n.id for n in created_notifications])],
                'target': 'current',
            }
    
    # action_reject is replaced by action_send_back in mixin
    # action_submit is inherited from mixin
    
    def action_generate_order(self):
        """Generate Expert Committee Order - Opens wizard with current report's project"""
        self.ensure_one()
        return {
            'name': _('Generate Expert Committee Order / विशेषज्ञ समिति आदेश जेनरेट करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.expert.committee.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
            }
        }


class ExpertCommitteeOrderWizard(models.TransientModel):
    _name = 'bhu.expert.committee.order.wizard'
    _description = 'Expert Committee Order Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)

    def action_generate_order(self):
        """Generate Order - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Order generation will be implemented soon.'),
                'type': 'info',
            }
        }


