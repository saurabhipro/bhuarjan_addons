# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class SiaTeam(models.Model):
    _name = 'bhu.sia.team'
    _description = 'SIA Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    _sql_constraints = [
        ('unique_project', 'UNIQUE(project_id)', 
         'Only one SIA Team can be created per project! / प्रति परियोजना केवल एक SIA टीम बनाई जा सकती है!')
    ]

    name = fields.Char(string='Team Name / टीम का नाम', compute='_compute_name', store=True, readonly=True)
    
    # New fields
    sub_division_id = fields.Many2one('bhu.sub.division', string='Sub Division / उपभाग', required=False, tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    requiring_body_id = fields.Many2one('bhu.department', string='Requiring Body / अपेक्षक निकाय', required=True, tracking=True,
                                       help='Select the requiring body/department', related="project_id.department_id")
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=False, tracking=True)
    village_ids = fields.Many2many('bhu.village', string='Affected Villages / प्रभावित ग्राम', tracking=True,
                                   help='Affected villages for this SIA Team (auto-populated from project)')
    tehsil_ids = fields.Many2many('bhu.tehsil', string='Tehsil / तहसील', compute='_compute_tehsil_ids', store=False, readonly=True,
                                  help='Tehsils from the selected villages')
    
    # Workflow
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / अनुमोदित'),
        ('rejected', 'Rejected / अस्वीकृत'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # SIA Team Members - 5 Sections
    # (क) Non-Government Social Scientist
    non_govt_social_scientist_ids = fields.Many2many('bhu.sia.team.member', 
                                                     'sia_team_non_govt_social_scientist_rel',
                                                     'sia_team_id', 'member_id',
                                                     string='Non-Government Social Scientist / गैर शासकीय सामाजिक वैज्ञानिक',
                                                     tracking=True)
    
    # (ख) Representatives of Local Bodies
    local_bodies_representative_ids = fields.Many2many('bhu.sia.team.member',
                                                       'sia_team_local_bodies_rep_rel',
                                                       'sia_team_id', 'member_id',
                                                       string='Representatives of Local Bodies / स्थानीय निकायों के प्रतिनिधि',
                                                       tracking=True)
    
    # (ग) Resettlement Expert
    resettlement_expert_ids = fields.Many2many('bhu.sia.team.member',
                                                'sia_team_resettlement_expert_rel',
                                                'sia_team_id', 'member_id',
                                                string='Resettlement Expert / पुनर्व्यवस्थापन विशेषज्ञ',
                                                tracking=True)
    
    # (घ) Technical Expert on Project Related Subject
    technical_expert_ids = fields.Many2many('bhu.sia.team.member',
                                            'sia_team_technical_expert_rel',
                                            'sia_team_id', 'member_id',
                                            string='Technical Expert / परियोजना से संबंधित विषय का तकनीकि विशेषज्ञ',
                                            tracking=True)
    
    # (ड.) Tehsildar of Affected Area (Convener)
    tehsildar_id = fields.Many2one('res.users',
                                   string='Tehsildar (Convener) / प्रभावित क्षेत्र का तहसीलदार',
                                   tracking=True,
                                   help='Tehsildar of the affected area who will be the convener')
    
    # Documents
    sia_file = fields.Binary(string='SIA File / SIA फ़ाइल')
    sia_filename = fields.Char(string='SIA Filename')
    
    # Signed SIA Reports
    sdm_signed_file = fields.Binary(string='SDM Signed SIA Report / SDM हस्ताक्षरित SIA रिपोर्ट', 
                                     help='Upload the signed SIA report from SDM')
    sdm_signed_filename = fields.Char(string='SDM Signed Filename')
    collector_signed_file = fields.Binary(string='Collector Signed SIA Report / कलेक्टर हस्ताक्षरित SIA रिपोर्ट',
                                          help='Upload the signed SIA report from Collector')
    collector_signed_filename = fields.Char(string='Collector Signed Filename')
    
    # Legacy fields (kept for backward compatibility)
    team_member_ids = fields.Many2many('bhu.sia.team.member', string='Team Members / टीम सदस्य', 
                                      compute='_compute_team_members', store=False)
    
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
    
    @api.depends('village_ids', 'village_ids.tehsil_id')
    def _compute_tehsil_ids(self):
        """Compute tehsils from selected villages"""
        for record in self:
            if record.village_ids:
                tehsils = record.village_ids.mapped('tehsil_id').filtered(lambda t: t)
                record.tehsil_ids = tehsils
            else:
                record.tehsil_ids = False
    
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
    
    @api.depends('project_id', 'project_id.village_ids', 'village_ids')
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
    tehsildar_domain = fields.Char()
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Auto-set tehsildar and villages based on project selection"""
        # Reset tehsildar when project changes
        for rec in self:
            if rec.project_id:
                rec.tehsildar_id = rec.project_id.tehsildar_ids[:1].id or False
                rec.tehsildar_domain = json.dumps([('id', 'in', rec.project_id.tehsildar_ids.ids)])
                
            else:
                rec.tehsildar_id = False
                rec.tehsildar_domain = False
        self.tehsildar_id = False

        
        
        # Auto-populate villages with all project villages only on new records or when project changes
        if not self._origin or (self._origin and self._origin.project_id != self.project_id):
            if self.project_id and self.project_id.village_ids:
                self.village_ids = self.project_id.village_ids
            else:
                self.village_ids = False
        
        domain_updates = {}
        
        if self.project_id and self.project_id.tehsildar_ids:
            # Get Tehsildar user IDs from the project
            tehsildar_user_ids = self.project_id.tehsildar_ids.ids
            
            # Find SIA Team Members that are linked to the project's Tehsildars
            sia_team_members = self.env['bhu.sia.team.member'].search([
                ('user_id', 'in', tehsildar_user_ids)
            ])
            
            # Auto-set if matches found
            if len(sia_team_members) == 1:
                self.tehsildar_id = sia_team_members[0]
            elif len(sia_team_members) > 1:
                # If multiple matches, set the first one (user can change if needed)
                self.tehsildar_id = sia_team_members[0]
            
            # Set domain to only show SIA Team Members linked to project's Tehsildars
            domain_updates['tehsildar_id'] = [('user_id', 'in', tehsildar_user_ids)]
        else:
            # If no project or no Tehsildars, restrict to empty (user must select project first)
            domain_updates['tehsildar_id'] = [('id', '=', False)]
        
        # Set domain for villages to only show project villages
        if self.project_id and self.project_id.village_ids:
            village_ids = self.project_id.village_ids.ids
            domain_updates['village_ids'] = [('id', 'in', village_ids)]
        else:
            domain_updates['village_ids'] = [('id', '=', False)]
        
        return {'domain': domain_updates}
    
    @api.constrains('project_id')
    def _check_unique_project(self):
        """Ensure only one SIA Team per project"""
        for record in self:
            if record.project_id:
                existing = self.search([
                    ('id', '!=', record.id),
                    ('project_id', '=', record.project_id.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _('A SIA Team already exists for project "%s". Only one SIA Team can be created per project.') %
                        record.project_id.name
                    )
    
    @api.constrains('village_ids', 'project_id')
    def _check_villages_belong_to_project(self):
        """Ensure selected villages belong to the project"""
        for record in self:
            if record.village_ids and record.project_id:
                invalid_villages = record.village_ids.filtered(
                    lambda v: v not in record.project_id.village_ids
                )
                if invalid_villages:
                    raise ValidationError(
                        _('The following villages do not belong to the selected project: %s') %
                        ', '.join(invalid_villages.mapped('name'))
                    )
    
    @api.constrains('non_govt_social_scientist_ids', 'local_bodies_representative_ids', 
                    'resettlement_expert_ids', 'technical_expert_ids', 'tehsildar_id')
    def _check_all_team_members_filled(self):
        """Validate that all team member sections are filled"""
        for record in self:
            missing_fields = []
            
            if not record.non_govt_social_scientist_ids:
                missing_fields.append(_('Non-Government Social Scientist / गैर शासकीय सामाजिक वैज्ञानिक'))
            
            if not record.local_bodies_representative_ids:
                missing_fields.append(_('Representatives of Local Bodies / स्थानीय निकायों के प्रतिनिधि'))
            
            if not record.resettlement_expert_ids:
                missing_fields.append(_('Resettlement Expert / पुनर्व्यवस्थापन विशेषज्ञ'))
            
            if not record.technical_expert_ids:
                missing_fields.append(_('Technical Expert / परियोजना से संबंधित विषय का तकनीकि विशेषज्ञ'))
            
            if not record.tehsildar_id:
                missing_fields.append(_('Tehsildar (Convener) / प्रभावित क्षेत्र का तहसीलदार'))
            
            if missing_fields:
                error_message = _('Please fill in all team member sections:\n\n%s') % '\n'.join(['- ' + field for field in missing_fields])
                raise ValidationError(error_message)
    
    @api.depends('project_id')
    def _compute_name(self):
        """Generate team name from project"""
        for record in self:
            if record.project_id:
                sequence = self.env['ir.sequence'].next_by_code('bhu.sia.team') or 'New'
                record.name = f'SIA-{sequence}'
            else:
                record.name = 'New'
    
    @api.depends('non_govt_social_scientist_ids', 'local_bodies_representative_ids', 
                 'resettlement_expert_ids', 'technical_expert_ids', 'tehsildar_id')
    def _compute_team_members(self):
        """Compute all team members from all sections"""
        for record in self:
            all_members = record.non_govt_social_scientist_ids
            all_members |= record.local_bodies_representative_ids
            all_members |= record.resettlement_expert_ids
            all_members |= record.technical_expert_ids
            if record.tehsildar_id:
                all_members |= record.tehsildar_id
            record.team_member_ids = all_members
    
    # Workflow Actions
    def action_submit(self):
        """Submit SIA Team for approval by Collector (SDM action)"""
        self.ensure_one()
        
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can submit SIA Team for approval.'))
        
        # Validate that SDM signed file is uploaded
        if not self.sdm_signed_file:
            raise ValidationError(_('Please upload the SDM signed SIA report before submitting.'))
        
        # Validate all team members are filled
        self._check_all_team_members_filled()
        
        self.state = 'submitted'
        self.message_post(body=_('SIA Team submitted for Collector approval by %s') % self.env.user.name)
    
    def action_approve(self):
        """Approve SIA Team (Collector action)"""
        self.ensure_one()
        
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can approve SIA Team.'))
        
        # Validate that Collector signed file is uploaded
        if not self.collector_signed_file:
            raise ValidationError(_('Please upload the Collector signed SIA report before approving.'))
        
        # Validate state is submitted
        if self.state != 'submitted':
            raise ValidationError(_('Only submitted SIA Teams can be approved.'))
        
        self.state = 'approved'
        self.message_post(body=_('SIA Team approved by %s') % self.env.user.name)
    
    def action_reject(self):
        """Reject SIA Team (Collector action)"""
        self.ensure_one()
        
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can reject SIA Team.'))
        
        # Validate state is submitted
        if self.state != 'submitted':
            raise ValidationError(_('Only submitted SIA Teams can be rejected.'))
        
        self.state = 'rejected'
        self.message_post(body=_('SIA Team rejected by %s') % self.env.user.name)
    
    def action_draft(self):
        """Reset to draft (only allowed when rejected)"""
        self.ensure_one()
        
        # Only allow reset to draft if rejected
        if self.state != 'rejected':
            raise ValidationError(_('Only rejected SIA Teams can be reset to draft.'))
        
        self.state = 'draft'
        self.message_post(body=_('SIA Team reset to draft by %s') % self.env.user.name)
    
    # Document Actions
    def action_download_sia_file(self):
        """Generate and download SIA Order Report PDF (unsigned)"""
        self.ensure_one()
        return self.env.ref('bhuarjan.action_report_sia_order').report_action(self)
    
    def action_download_sdm_signed_file(self):
        """Download SDM signed SIA report"""
        self.ensure_one()
        if not self.sdm_signed_file:
            raise ValidationError(_('SDM signed SIA report is not available.'))
        filename = self.sdm_signed_filename or 'sdm_signed_sia_report.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/bhu.sia.team/{self.id}/sdm_signed_file/{filename}?download=true',
            'target': 'self',
        }
    
    def action_download_collector_signed_file(self):
        """Download Collector signed SIA report"""
        self.ensure_one()
        if not self.collector_signed_file:
            raise ValidationError(_('Collector signed SIA report is not available.'))
        filename = self.collector_signed_filename or 'collector_signed_sia_report.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/bhu.sia.team/{self.id}/collector_signed_file/{filename}?download=true',
            'target': 'self',
        }
    
    
    def action_create_section4_notification(self):
        """Create Section 4 Notifications for all villages in this SIA Team"""
        self.ensure_one()
        
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        
        if not self.requiring_body_id:
            raise ValidationError(_('Please select a requiring body first.'))
        
        if not self.village_ids:
            raise ValidationError(_('Please select at least one village first.'))
        
        # Create Section 4 Notifications for each village
        created_notifications = []
        skipped_villages = []
        
        for village in self.village_ids:
            # Check if notification already exists for this village and project
            existing = self.env['bhu.section4.notification'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', village.id)
            ], limit=1)
            
            if existing:
                skipped_villages.append(village.name)
                continue
            
            # Check if surveys exist for this village
            surveys = self.env['bhu.survey'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', village.id)
            ])
            
            if not surveys:
                skipped_villages.append(f"{village.name} (no surveys)")
                continue
            
            # Create notification
            notification = self.env['bhu.section4.notification'].create({
                'project_id': self.project_id.id,
                'village_id': village.id,
                'requiring_body_id': self.requiring_body_id.id,
            })
            created_notifications.append(notification)
        
        if created_notifications:
            # Add message to SIA Team record about created notifications
            if skipped_villages:
                message = _('Created %d Section 4 Notification(s) from this SIA Team. Skipped villages: %s') % (
                    len(created_notifications),
                    ', '.join(skipped_villages)
                )
            else:
                message = _('Created %d Section 4 Notification(s) from this SIA Team.') % len(created_notifications)
            
            self.message_post(body=message)
            
            # Open the first created notification in form view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Section 4 Notifications'),
                'res_model': 'bhu.section4.notification',
                'res_id': created_notifications[0].id if len(created_notifications) == 1 else False,
                'view_mode': 'form' if len(created_notifications) == 1 else 'list,form',
                'domain': [('id', 'in', [n.id for n in created_notifications])] if len(created_notifications) > 1 else [],
                'target': 'current',
                'context': {
                    'default_project_id': self.project_id.id,
                    'default_requiring_body_id': self.requiring_body_id.id,
                }
            }
        else:
            # Show error if no notifications were created
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No notifications were created. All villages either already have notifications or have no surveys.'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
    

