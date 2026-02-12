# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DashboardCounts(models.AbstractModel):
    """Dashboard count calculation methods"""
    _name = 'bhuarjan.dashboard.counts'
    _description = 'Dashboard Count Methods'

    @api.model
    def _get_all_counts(self, project_id=None, village_id=None, department_id=None):
        """Get all counts - cached computation"""
        # Build domain filters
        project_domain = [('project_id', '=', project_id)] if project_id else []
        village_domain = []
        
        # Handle village filtering - simplified logic
        if village_id:
            # Village is selected - always filter by village
            # If project is also selected, the domain will combine both (AND condition)
            village_domain = [('village_id', '=', village_id)]
        elif project_id:
            # Project selected but no village - show ALL surveys for this project
            # Don't restrict to project.village_ids because some villages might have surveys
            # but not be in the Many2many relationship (like Jurda)
            # Just filter by project_id - the surveys will naturally be for villages in that project
            village_domain = []  # No village filter - show all villages with surveys in this project
        
        # If department is selected but no project, filter projects by department
        if department_id and not project_id:
            department_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
            if department_projects:
                project_ids = department_projects.ids
                project_domain = [('project_id', 'in', project_ids)]
            else:
                # No projects for this department, return zeros for project-related counts
                project_domain = [('project_id', '=', False)]  # This will return 0 results
        
        # Base domains for sections - combine project and village filters
        # Note: expert_committee_report and sia_team don't have village_id field, so exclude village_domain for them
        has_filters = (project_id or village_id or department_id)
        section4_base = project_domain + village_domain if has_filters else []
        section11_base = project_domain + village_domain if has_filters else []
        section19_base = project_domain + village_domain if has_filters else []
        section15_base = project_domain + village_domain if has_filters else []
        # Expert and SIA don't have village_id - only use project_domain
        expert_base = project_domain if (project_id or department_id) else []
        sia_base = project_domain if (project_id or department_id) else []
        section23_base = project_domain + village_domain if has_filters else []
        payment_base = project_domain + village_domain if has_filters else []
        reconciliation_base = project_domain + village_domain if has_filters else []
        
        # Survey domain - combine project and village filters properly
        survey_base = []
        if project_id or village_id or department_id:
            # ... existing logic ...
            if project_domain and village_domain:
                survey_base = project_domain + village_domain
            elif project_domain:
                survey_base = project_domain
            elif village_domain:
                survey_base = village_domain
            else:
                survey_base = project_domain
        
        # ... (logging and test query) ...

        # Get section counts using generic methods
        section4_counts = self._get_section_counts('bhu.section4.notification', section4_base)
        section11_counts = self._get_section_counts('bhu.section11.preliminary.report', section11_base)
        section19_counts = self._get_section_counts('bhu.section19.notification', section19_base)
        section15_counts = self._get_section_counts('bhu.section15.objection', section15_base)
        expert_counts = self._get_section_counts('bhu.expert.committee.report', expert_base)
        sia_counts = self._get_section_counts('bhu.sia.team', sia_base)
        section23_counts = self._get_section_counts('bhu.section23.award', section23_base)
        
        return {
            # ... existing counts ...

            # SIA Teams - using generic method
            'sia_total': sia_counts['total'],
            'sia_draft': sia_counts['draft'],
            'sia_submitted': sia_counts['submitted'],
            'sia_approved': sia_counts['approved'],
            'sia_send_back': sia_counts['send_back'],
            
            # Section 23 Awards - using generic method
            'section23_total': section23_counts['total'],
            'section23_draft': section23_counts['draft'],
            'section23_submitted': section23_counts['submitted'],
            'section23_approved': section23_counts['approved'],
            'section23_send_back': section23_counts['send_back'],
            
            # Payment Files
            'payment_file_total': self.env['bhu.payment.file'].search_count(payment_base),
            'payment_file_draft': self.env['bhu.payment.file'].search_count(payment_base + [('state', '=', 'draft')]),
            'payment_file_generated': self.env['bhu.payment.file'].search_count(payment_base + [('state', '=', 'generated')]),
            
            # Payment Reconciliations
            'reconciliation_total': self.env['bhu.payment.reconciliation.bank'].search_count(reconciliation_base),
            'reconciliation_draft': self.env['bhu.payment.reconciliation.bank'].search_count(reconciliation_base + [('state', '=', 'draft')]),
            'reconciliation_processed': self.env['bhu.payment.reconciliation.bank'].search_count(reconciliation_base + [('state', '=', 'processed')]),
            'reconciliation_completed': self.env['bhu.payment.reconciliation.bank'].search_count(reconciliation_base + [('state', '=', 'completed')]),
            
            # Document Vault
            'total_documents': self.env['bhu.document.vault'].search_count([]),
            
            # Active Mobile Users (unique users with JWT tokens from mobile channel)
            'active_mobile_users': len(set(self.env['jwt.token'].search([('channel_type', '=', 'mobile')]).mapped('user_id').ids)),
        }

