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

    def write(self, vals):
        """Override write to intercept state changes and validate them"""
        # Check if state is being changed
        if 'state' in vals:
            for record in self:
                old_state = record.state
                new_state = vals['state']
                
                # If state is changing, validate the transition
                if old_state != new_state:
                    # Build method name: _validate_state_to_<new_state>
                    method_name = f'_validate_state_to_{new_state}'
                    
                    # Check if validation method exists and call it
                    if hasattr(record, method_name):
                        method = getattr(record, method_name)
                        method()  # This will raise ValidationError if invalid
                    else:
                        # Fallback: validate basic transition rules
                        record._validate_state_transition(old_state, new_state)
                    
                    # If validation passes, post message
                    record._post_state_change_message(old_state, new_state)
        
        return super().write(vals)
    
    def _validate_state_transition(self, old_state, new_state):
        """Validate state transitions"""
        valid_transitions = {
            'draft': ['submitted'],
            'submitted': ['approved', 'send_back'],
            'approved': [],
            'send_back': ['draft'],
        }
        
        if new_state not in valid_transitions.get(old_state, []):
            raise ValidationError(
                _('Invalid state transition from %s to %s') % (
                    dict(self._fields['state'].selection)[old_state],
                    dict(self._fields['state'].selection)[new_state]
                )
            )
    
    def _post_state_change_message(self, old_state, new_state):
        """Post a message when state changes"""
        state_labels = dict(self._fields['state'].selection)
        self.message_post(
            body=_('Status changed from %s to %s by %s') % (
                state_labels[old_state],
                state_labels[new_state],
                self.env.user.name
            )
        )
    
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
    
    # Validation methods for statusbar click handling (called from write)
    def _validate_state_to_draft(self):
        """Validate transition to draft state"""
        self.ensure_one()
        # Allow going back to draft only from send_back state
        if self.state != 'send_back':
            raise ValidationError(_('Cannot change status to Draft from current state. Only sent back records can be reset to draft.'))
    
    def _validate_state_to_submitted(self):
        """Validate transition to submitted state"""
        self.ensure_one()
        # Allow going to submitted from draft state
        if self.state != 'draft':
            raise ValidationError(_('Cannot change status to Submitted from current state. Only draft records can be submitted.'))
        # Check if user is SDM
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only SDM can submit for approval.'))
        # Validate that SDM signed file is uploaded
        if not self.sdm_signed_file:
            raise ValidationError(_('Please upload the SDM signed document before submitting.'))
    
    def _validate_state_to_approved(self):
        """Validate transition to approved state"""
        self.ensure_one()
        # Allow going to approved from submitted state
        if self.state != 'submitted':
            raise ValidationError(_('Cannot change status to Approved from current state. Only submitted records can be approved.'))
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can approve.'))
        # Validate that Collector signed file is uploaded
        if not self.collector_signed_file:
            raise ValidationError(_('Please upload the Collector signed document before approving.'))
    
    def _validate_state_to_send_back(self):
        """Validate transition to send_back state"""
        self.ensure_one()
        # Allow going to send_back from submitted state
        if self.state != 'submitted':
            raise ValidationError(_('Cannot change status to Sent Back from current state. Only submitted records can be sent back.'))
        # Check if user is Collector
        if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
            raise ValidationError(_('Only Collector can send back.'))
        # Note: For send_back, we might want to open a wizard, but for statusbar clicks, we'll just validate
    
    # Methods for statusbar click handling (kept for backward compatibility)
    def set_state_draft(self):
        """Set state to draft when clicking on draft status button"""
        self.ensure_one()
        # Allow going back to draft only from send_back state
        if self.state == 'send_back':
            self.state = 'draft'
            self.message_post(body=_('Status changed to Draft by %s') % self.env.user.name)
        else:
            raise ValidationError(_('Cannot change status to Draft from current state.'))
    
    def set_state_submitted(self):
        """Set state to submitted when clicking on submitted status button"""
        self.ensure_one()
        # Allow going to submitted from draft state
        if self.state == 'draft':
            # Check if user is SDM
            if not (self.env.user.has_group('bhuarjan.group_bhuarjan_sdm') or 
                    self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
                raise ValidationError(_('Only SDM can submit for approval.'))
            # Validate that SDM signed file is uploaded
            if not self.sdm_signed_file:
                raise ValidationError(_('Please upload the SDM signed document before submitting.'))
            self.state = 'submitted'
            self.message_post(body=_('Status changed to Submitted by %s') % self.env.user.name)
        elif self.state == 'submitted':
            # Already in submitted state
            pass
        else:
            raise ValidationError(_('Cannot change status to Submitted from current state.'))
    
    def set_state_approved(self):
        """Set state to approved when clicking on approved status button"""
        self.ensure_one()
        # Allow going to approved from submitted state
        if self.state == 'submitted':
            # Check if user is Collector
            if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                    self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
                raise ValidationError(_('Only Collector can approve.'))
            # Validate that Collector signed file is uploaded
            if not self.collector_signed_file:
                raise ValidationError(_('Please upload the Collector signed document before approving.'))
            self.state = 'approved'
            self.message_post(body=_('Status changed to Approved by %s') % self.env.user.name)
        elif self.state == 'approved':
            # Already in approved state
            pass
        else:
            raise ValidationError(_('Cannot change status to Approved from current state.'))
    
    def set_state_send_back(self):
        """Set state to send_back when clicking on send_back status button"""
        self.ensure_one()
        # Allow going to send_back from submitted state
        if self.state == 'submitted':
            # Check if user is Collector
            if not (self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or 
                    self.env.user.has_group('bhuarjan.group_bhuarjan_admin')):
                raise ValidationError(_('Only Collector can send back.'))
            # Open wizard for send back
            return self.action_send_back()
        elif self.state == 'send_back':
            # Already in send_back state
            pass
        else:
            raise ValidationError(_('Cannot change status to Sent Back from current state.'))
    
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

