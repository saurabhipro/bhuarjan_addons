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
        
        # Survey domain - combine project and village filters properly
        survey_base = []
        if project_id or village_id or department_id:
            # Build domain with proper AND logic
            if project_domain and village_domain:
                # Both project and village filters - combine with AND
                survey_base = project_domain + village_domain
            elif project_domain:
                # Only project filter
                survey_base = project_domain
            elif village_domain:
                # Only village filter
                survey_base = village_domain
            else:
                # Only department filter (which affects project_domain)
                survey_base = project_domain
        
        # Log the domain for debugging
        _logger.info(f"Dashboard filters - project_id: {project_id}, village_id: {village_id}, department_id: {department_id}")
        _logger.info(f"Project domain: {project_domain}, Village domain: {village_domain}")
        _logger.info(f"Survey domain: {survey_base}")
        
        # Test query to verify domain works
        if survey_base:
            test_count = self.env['bhu.survey'].search_count(survey_base)
            _logger.info(f"Test survey count with domain: {test_count}")
        
        # Filter projects count by department if provided
        project_count_domain = []
        if department_id:
            project_count_domain = [('department_id', '=', department_id)]
        
        # Get survey counts using generic method
        survey_counts = self._get_survey_counts(survey_base)
        
        # Get section counts using generic methods
        section4_counts = self._get_section_counts('bhu.section4.notification', section4_base)
        section11_counts = self._get_section_counts('bhu.section11.preliminary.report', section11_base)
        section19_counts = self._get_section_counts('bhu.section19.notification', section19_base)
        section15_counts = self._get_section_counts('bhu.section15.objection', section15_base)
        expert_counts = self._get_section_counts('bhu.expert.committee.report', expert_base)
        sia_counts = self._get_section_counts('bhu.sia.team', sia_base)
        
        return {
            # Master Data Counts
            'total_districts': self.env['bhu.district'].search_count([]),
            'total_sub_divisions': self.env['bhu.sub.division'].search_count([]),
            'total_tehsils': self.env['bhu.tehsil'].search_count([]),
            'total_villages': self.env['bhu.village'].search_count(village_domain if village_id else []),
            'total_projects': self.env['bhu.project'].search_count(project_count_domain),
            'total_departments': self.env['bhu.department'].search_count([]),
            'total_landowners': self.env['bhu.landowner'].search_count([]),
            'total_rate_masters': self.env['bhu.rate.master'].search_count([]),
            
            # Survey Counts - using generic method
            'total_surveys': survey_counts['total'],
            'draft_surveys': survey_counts['draft'],
            'submitted_surveys': survey_counts['submitted'],
            'approved_surveys': survey_counts['approved'],
            'rejected_surveys': survey_counts['rejected'],
            'total_surveys_done': survey_counts['total_done'],
            'pending_surveys': survey_counts['pending'],
            'survey_completion_percent': survey_counts['completion_percent'],
            
            # Section 4 Notifications - using generic method
            'section4_total': section4_counts['total'],
            'section4_draft': section4_counts['draft'],
            'section4_submitted': section4_counts['submitted'],
            'section4_approved': section4_counts['approved'],
            'section4_send_back': section4_counts['send_back'],
            
            # Section 11 Reports - using generic method
            'section11_total': section11_counts['total'],
            'section11_draft': section11_counts['draft'],
            'section11_submitted': section11_counts['submitted'],
            'section11_approved': section11_counts['approved'],
            'section11_send_back': section11_counts['send_back'],
            
            # Section 19 Notifications - using generic method
            'section19_total': section19_counts['total'],
            'section19_draft': section19_counts['draft'],
            'section19_submitted': section19_counts['submitted'],
            'section19_approved': section19_counts['approved'],
            'section19_send_back': section19_counts['send_back'],
            
            # Section 15 Objections - using generic method
            'section15_total': section15_counts['total'],
            'section15_draft': section15_counts['draft'],
            'section15_submitted': section15_counts['submitted'],
            'section15_approved': section15_counts['approved'],
            'section15_send_back': section15_counts['send_back'],
            
            # Expert Committee Reports - using generic method
            'expert_committee_total': expert_counts['total'],
            'expert_committee_draft': expert_counts['draft'],
            'expert_committee_submitted': expert_counts['submitted'],
            'expert_committee_approved': expert_counts['approved'],
            'expert_committee_send_back': expert_counts['send_back'],
            
            # SIA Teams - using generic method
            'sia_total': sia_counts['total'],
            'sia_draft': sia_counts['draft'],
            'sia_submitted': sia_counts['submitted'],
            'sia_approved': sia_counts['approved'],
            'sia_send_back': sia_counts['send_back'],
            
            # Payment Files
            'total_payment_files': self.env['bhu.payment.file'].search_count([]),
            'draft_payment_files': self.env['bhu.payment.file'].search_count([('state', '=', 'draft')]),
            'generated_payment_files': self.env['bhu.payment.file'].search_count([('state', '=', 'generated')]),
            
            # Payment Reconciliations
            'total_payment_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([]),
            'draft_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'draft')]),
            'processed_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'processed')]),
            'completed_reconciliations': self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'completed')]),
            
            # Document Vault
            'total_documents': self.env['bhu.document.vault'].search_count([]),
            
            # Active Mobile Users (unique users with JWT tokens from mobile channel)
            'active_mobile_users': len(set(self.env['jwt.token'].search([('channel_type', '=', 'mobile')]).mapped('user_id').ids)),
        }

