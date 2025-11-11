# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid

class ExpertCommitteeReport(models.Model):
    _name = 'bhu.expert.committee.report'
    _description = 'Expert Committee Report / विशेषज्ञ समिति रिपोर्ट'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Report Name / रिपोर्ट का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True,
                                  default=lambda self: self._default_project_id(), tracking=True)
    
    _sql_constraints = [
        ('project_unique', 'UNIQUE(project_id)', 'Only one Expert Committee Report is allowed per project.')
    ]
    
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
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / स्वीकृत'),
        ('rejected', 'Rejected / अस्वीकृत'),
        ('signed', 'Signed / हस्ताक्षरित'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
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
    
    def action_approve(self):
        """Approve the Expert Committee Report"""
        self.ensure_one()
        if self.state not in ['draft', 'submitted']:
            raise ValidationError(_('Only draft or submitted reports can be approved.'))
        self.state = 'approved'
        return True
    
    def action_reject(self):
        """Reject the Expert Committee Report"""
        self.ensure_one()
        if self.state not in ['draft', 'submitted']:
            raise ValidationError(_('Only draft or submitted reports can be rejected.'))
        self.state = 'rejected'
        return True
    
    def action_submit(self):
        """Submit the Expert Committee Report for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Only draft reports can be submitted.'))
        self.state = 'submitted'
        return True
    
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


