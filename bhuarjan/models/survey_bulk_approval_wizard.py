# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SurveyBulkApprovalWizard(models.TransientModel):
    _name = 'bhu.survey.bulk.approval.wizard'
    _description = 'Survey Bulk Approval Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम',
                                   help="Select specific villages to approve surveys for. If none selected, all villages in the project will be considered.")
    approval_remarks = fields.Text(string='Approval Remarks / अनुमोदन टिप्पणी', required=True)
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset villages when project changes and set domain"""
        self.village_ids = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_ids': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_ids': []}}

    def action_approve_surveys(self):
        """Approve surveys based on selected project and villages"""
        self.ensure_one()
        
        # Build domain for surveys to approve
        domain = [
            ('project_id', '=', self.project_id.id),
            ('state', 'in', ['draft', 'submitted'])  # Allow approving draft or submitted surveys
        ]
        
        # Filter by villages if selected
        if self.village_ids:
            domain.append(('village_id', 'in', self.village_ids.ids))
        
        # Find surveys matching criteria
        surveys = self.env['bhu.survey'].search(domain)
        
        if not surveys:
            # Provide helpful error message
            if self.village_ids:
                village_names = ', '.join(self.village_ids.mapped('name'))
                raise ValidationError(_('No draft or submitted surveys found for project "%s" and village(s): %s.\n\nPlease check:\n- Survey state (should be Draft or Submitted)\n- Project and Village selection') % (self.project_id.name, village_names))
            else:
                raise ValidationError(_('No draft or submitted surveys found for project "%s".\n\nPlease check:\n- Survey state (should be Draft or Submitted)\n- Project selection') % self.project_id.name)
        
        # Approve surveys using the existing approve method
        approved_count = 0
        for survey in surveys:
            try:
                if survey.state in ['draft', 'submitted']:
                    survey.action_approve()  # Use the existing approve method
                    survey.message_post(
                        body=_('Bulk approved by %s\n\nApproval Remarks: %s') % (self.env.user.name, self.approval_remarks),
                        message_type='notification'
                    )
                    approved_count += 1
            except Exception as e:
                # Log error but continue with other surveys
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error("Error approving survey %s: %s", survey.name, e)
        
        if approved_count == 0:
            raise ValidationError(_('No surveys could be approved. Please check survey states and permissions.'))
        
        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d survey(s) approved successfully for project %s.') % (approved_count, self.project_id.name),
                'type': 'success',
                'sticky': False,
            }
        }

