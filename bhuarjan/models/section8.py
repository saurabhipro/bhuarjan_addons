# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class Section8(models.Model):
    _name = 'bhu.section8'
    _description = 'Section 8'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Section 8 Reference / धारा 8 संदर्भ', required=True, tracking=True, default='New', readonly=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', 
                                    related='project_id.department_id', 
                                    store=True, readonly=True, tracking=True,
                                    help='Department automatically derived from selected project')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', tracking=True)
    
    # Satisfaction fields
    is_satisfied = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Are you satisfied? / क्या आप संतुष्ट हैं?', tracking=True)
    dissatisfaction_reason = fields.Text(string='Reason for Dissatisfaction / असंतुष्टि का कारण', tracking=True)
    
    # File upload (optional)
    attachment_file = fields.Binary(string='Attachment / अनुलग्नक', tracking=True)
    attachment_filename = fields.Char(string='Attachment Filename / अनुलग्नक फ़ाइल नाम', tracking=True)
    
    # State for Approve/Reject
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
    # Approval/Rejection details
    approval_date = fields.Datetime(string='Approval Date / अनुमोदन दिनांक', readonly=True, tracking=True)
    approval_reason = fields.Text(string='Approval Reason / अनुमोदन का कारण', tracking=True)
    rejection_date = fields.Datetime(string='Rejection Date / अस्वीकृति दिनांक', readonly=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason / अस्वीकृति का कारण', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    village_domain = fields.Char()
    project_domain = fields.Char()
    
    # Computed field to check if current user is SDM (for readonly)
    is_sdm_user = fields.Boolean(string='Is SDM User', compute='_compute_is_sdm_user', store=False)
    
    @api.depends()
    def _compute_is_sdm_user(self):
        """Compute if current user is SDM"""
        is_sdm = self.env.user.has_group('bhuarjan.group_bhuarjan_sdm')
        for rec in self:
            rec.is_sdm_user = is_sdm
    
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([('id', 'in', [])])
                rec.village_id = False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate section 8 reference if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section8', project_id, village_id=village_id if village_id else None
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        sequence = self.env['ir.sequence'].next_by_code('bhu.section8') or 'New'
                        vals['name'] = f'SEC8-{sequence}'
                else:
                    # No project_id, use fallback
                    sequence = self.env['ir.sequence'].next_by_code('bhu.section8') or 'New'
                    vals['name'] = f'SEC8-{sequence}'
        return super().create(vals_list)
    
    def action_approve(self):
        """Open wizard to approve Section 8"""
        self.ensure_one()
        if self.state == 'approved':
            raise ValidationError(_('Section 8 is already approved.'))
        
        wizard = self.env['bhu.section8.approve.reject.wizard'].create({
            'res_id': self.id,
            'action_type': 'approve',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Section 8'),
            'res_model': 'bhu.section8.approve.reject.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_reject(self):
        """Open wizard to reject Section 8"""
        self.ensure_one()
        if self.state == 'rejected':
            raise ValidationError(_('Section 8 is already rejected.'))
        
        wizard = self.env['bhu.section8.approve.reject.wizard'].create({
            'res_id': self.id,
            'action_type': 'reject',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Section 8'),
            'res_model': 'bhu.section8.approve.reject.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_download_sia_report(self):
        """Download SIA Report for the project"""
        self.ensure_one()
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        
        # Find SIA team for this project
        sia_team = self.env['bhu.sia.team'].search([
            ('project_id', '=', self.project_id.id)
        ], limit=1, order='create_date desc')
        
        if not sia_team:
            raise ValidationError(_('No SIA Team found for this project.'))
        
        # Download SIA Order (SDM's proposal)
        return self.env.ref('bhuarjan.action_report_sia_order').report_action(sia_team)
    
    def action_download_expert_report(self):
        """Download Expert Committee Report for the project"""
        self.ensure_one()
        if not self.project_id:
            raise ValidationError(_('Please select a project first.'))
        
        # Find Expert Committee report for this project
        expert_report = self.env['bhu.expert.committee.report'].search([
            ('project_id', '=', self.project_id.id)
        ], limit=1, order='create_date desc')
        
        if not expert_report:
            raise ValidationError(_('No Expert Committee Report found for this project.'))
        
        # Download Expert Committee Order
        return self.env.ref('bhuarjan.action_report_expert_committee_order').report_action(expert_report)

