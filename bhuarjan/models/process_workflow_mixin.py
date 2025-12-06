# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProcessWorkflowMixin(models.AbstractModel):
    """Common workflow mixin for all process forms (SIA, Expert Committee, Section 4, 11, 19)"""
    _name = 'bhu.process.workflow.mixin'
    _description = 'Process Workflow Mixin'

    # Common workflow state
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / अनुमोदित'),
        ('send_back', 'Sent Back / वापस भेजा गया'),
    ], string='Status / स्थिति', default='draft', tracking=True)

    # SDM signed file
    sdm_signed_file = fields.Binary(string='SDM Signed Document / SDM हस्ताक्षरित दस्तावेज़', 
                                    help='Upload the signed document from SDM')
    sdm_signed_filename = fields.Char(string='SDM Signed Filename')

    # Collector signed file
    collector_signed_file = fields.Binary(string='Collector Signed Document / कलेक्टर हस्ताक्षरित दस्तावेज़',
                                         help='Upload the signed document from Collector')
    collector_signed_filename = fields.Char(string='Collector Signed Filename')

    # Common workflow methods
    def action_submit(self):
        """Submit for approval by Collector (SDM action)"""
        self.ensure_one()
        
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can submit for approval.'))
        
        # Validate that SDM signed file is uploaded
        if not self.sdm_signed_file:
            raise ValidationError(_('Please upload the SDM signed document before submitting.'))
        
        self.state = 'submitted'
        self.message_post(body=_('Submitted for Collector approval by %s') % self.env.user.name)
    
    def action_approve(self):
        """Approve (Collector action)"""
        self.ensure_one()
        
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can approve.'))
        
        # Validate that Collector signed file is uploaded
        if not self.collector_signed_file:
            raise ValidationError(_('Please upload the Collector signed document before approving.'))
        
        # Validate state is submitted
        if self.state != 'submitted':
            raise ValidationError(_('Only submitted records can be approved.'))
        
        self.state = 'approved'
        self.message_post(body=_('Approved by %s') % self.env.user.name)
    
    def action_send_back(self):
        """Open wizard to send back (Collector action)"""
        self.ensure_one()
        
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can send back.'))
        
        # Validate state is submitted
        if self.state != 'submitted':
            raise ValidationError(_('Only submitted records can be sent back.'))
        
        # Open wizard - use model name to determine wizard model
        wizard_model = 'process.send.back.wizard'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Back'),
            'res_model': wizard_model,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }
    
    def action_draft(self):
        """Reset to draft (only allowed when sent back) - allows SDM to resubmit"""
        self.ensure_one()
        
        # Only allow reset to draft if sent back
        if self.state != 'send_back':
            raise ValidationError(_('Only sent back records can be reset to draft for resubmission.'))
        
        self.state = 'draft'
        self.message_post(body=_('Reset to draft by %s for resubmission') % self.env.user.name)
    
    def action_download_unsigned_file(self):
        """Download unsigned document - to be overridden by each model"""
        self.ensure_one()
        raise ValidationError(_('This method must be overridden in the model.'))
    
    def action_download_sdm_signed_file(self):
        """Download SDM signed document"""
        self.ensure_one()
        if not self.sdm_signed_file:
            raise ValidationError(_('SDM signed document is not available.'))
        filename = self.sdm_signed_filename or 'sdm_signed_document.pdf'
        # Use model name with dots (Odoo's standard format for /web/content/)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/sdm_signed_file/{filename}?download=true',
            'target': 'self',
        }
    
    def action_download_collector_signed_file(self):
        """Download Collector signed document"""
        self.ensure_one()
        if not self.collector_signed_file:
            raise ValidationError(_('Collector signed document is not available.'))
        filename = self.collector_signed_filename or 'collector_signed_document.pdf'
        # Use model name with dots (Odoo's standard format for /web/content/)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/collector_signed_file/{filename}?download=true',
            'target': 'self',
        }

