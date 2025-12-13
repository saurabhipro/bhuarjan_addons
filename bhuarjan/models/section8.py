# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class Section8(models.Model):
    _name = 'bhu.section8'
    _description = 'Section 8'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Section 8 Reference / धारा 8 संदर्भ', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # State for Approve/Reject
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
    # Approval/Rejection details
    approval_date = fields.Datetime(string='Approval Date / अनुमोदन दिनांक', readonly=True, tracking=True)
    rejection_date = fields.Datetime(string='Rejection Date / अस्वीकृति दिनांक', readonly=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason / अस्वीकृति का कारण', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes / नोट्स', tracking=True)
    
    village_domain = fields.Char()
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        for rec in self:
            if rec.project_id and rec.project_id.village_ids:
                rec.village_domain = json.dumps([('id', 'in', rec.project_id.village_ids.ids)])
            else:
                rec.village_domain = json.dumps([])
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
                        'section8', project_id, village_id=village_id
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
        """Approve Section 8"""
        for record in self:
            if record.state == 'approved':
                raise ValidationError(_('Section 8 is already approved.'))
            record.state = 'approved'
            record.approval_date = fields.Datetime.now()
            record.message_post(
                body=_('Section 8 approved by %s') % self.env.user.name,
                message_type='notification'
            )
    
    def action_reject(self):
        """Reject Section 8"""
        for record in self:
            if record.state == 'rejected':
                raise ValidationError(_('Section 8 is already rejected.'))
            if not record.rejection_reason:
                raise ValidationError(_('Please provide a rejection reason.'))
            record.state = 'rejected'
            record.rejection_date = fields.Datetime.now()
            record.message_post(
                body=_('Section 8 rejected by %s. Reason: %s') % (self.env.user.name, record.rejection_reason),
                message_type='notification'
            )

