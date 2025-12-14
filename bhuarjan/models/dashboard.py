# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class BhuarjanDashboard(models.TransientModel):
    _name = 'bhuarjan.dashboard'
    _description = 'Bhuarjan Dashboard'

    current_datetime = fields.Char(string='Current Date & Time', compute='_compute_current_datetime', store=False)
    
    @api.model
    def default_get(self, fields_list):
        """Set default values including current datetime"""
        res = super().default_get(fields_list)
        
        return res
    
    @api.depends()
    def _compute_current_datetime(self):
        """Compute current date and time as formatted string"""
        from datetime import datetime
        for record in self:
            now = datetime.now()
            record.current_datetime = now.strftime('%Y-%m-%d %H:%M:%S') or 'Loading...'

    is_admin = fields.Boolean(string='Is Admin', compute='_compute_is_admin', store=False)
    
    @api.depends()
    def _compute_is_admin(self):
        """Check if current user is admin"""
        for record in self:
            try:
                record.is_admin = self.env.user.has_group('bhuarjan.group_bhuarjan_admin') or self.env.user.has_group('base.group_system')
            except:
                record.is_admin = False
    

    

    

    # Master Data Counts
    total_districts = fields.Integer(string='Total Districts', readonly=True, default=0)
    total_sub_divisions = fields.Integer(string='Total Sub Divisions', readonly=True, default=0)
    total_tehsils = fields.Integer(string='Total Tehsils', readonly=True, default=0)
    total_villages = fields.Integer(string='Total Villages', readonly=True, default=0)
    total_projects = fields.Integer(string='Total Projects', readonly=True, default=0)
    total_departments = fields.Integer(string='Total Departments', readonly=True, default=0)
    total_landowners = fields.Integer(string='Total Landowners', readonly=True, default=0)
    total_rate_masters = fields.Integer(string='Total Rate Masters', readonly=True, default=0)
    
    # Survey Counts
    total_surveys = fields.Integer(string='Total Surveys', readonly=True, default=0)
    draft_surveys = fields.Integer(string='Draft Surveys', readonly=True, default=0)
    submitted_surveys = fields.Integer(string='Submitted Surveys', readonly=True, default=0)
    approved_surveys = fields.Integer(string='Approved Surveys', readonly=True, default=0)
    rejected_surveys = fields.Integer(string='Rejected Surveys', readonly=True, default=0)
    total_surveys_done = fields.Integer(string='Total Surveys Done', readonly=True, default=0)
    pending_surveys = fields.Integer(string='Pending Surveys', readonly=True, default=0)
    
    # Process Counts
    total_section4_notifications = fields.Integer(string='Section 4 Notifications', readonly=True, default=0)
    draft_section4 = fields.Integer(string='Draft Section 4', readonly=True, default=0)
    generated_section4 = fields.Integer(string='Generated Section 4', readonly=True, default=0)
    signed_section4 = fields.Integer(string='Signed Section 4', readonly=True, default=0)
    
    total_section11_reports = fields.Integer(string='Section 11 Reports', readonly=True, default=0)
    draft_section11 = fields.Integer(string='Draft Section 11', readonly=True, default=0)
    generated_section11 = fields.Integer(string='Generated Section 11', readonly=True, default=0)
    signed_section11 = fields.Integer(string='Signed Section 11', readonly=True, default=0)
    
    total_expert_committee_reports = fields.Integer(string='Expert Committee Reports', readonly=True, default=0)
    total_section15_objections = fields.Integer(string='Section 15 Objections', readonly=True, default=0)
    
    # Section 19 Notifications
    total_section19_notifications = fields.Integer(string='Section 19 Notifications', readonly=True, default=0)
    draft_section19 = fields.Integer(string='Draft Section 19', readonly=True, default=0)
    generated_section19 = fields.Integer(string='Generated Section 19', readonly=True, default=0)
    signed_section19 = fields.Integer(string='Signed Section 19', readonly=True, default=0)
    
    # SIA Team Counts
    total_sia_teams = fields.Integer(string='Total SIA Teams', readonly=True, default=0)
    draft_sia_teams = fields.Integer(string='Draft SIA Teams', readonly=True, default=0)
    submitted_sia_teams = fields.Integer(string='Submitted SIA Teams', readonly=True, default=0)
    approved_sia_teams = fields.Integer(string='Approved SIA Teams', readonly=True, default=0)
    send_back_sia_teams = fields.Integer(string='Send Back SIA Teams', readonly=True, default=0)
    
    # Payment File Counts
    total_payment_files = fields.Integer(string='Payment Files', readonly=True, default=0)
    draft_payment_files = fields.Integer(string='Draft Payment Files', readonly=True, default=0)
    generated_payment_files = fields.Integer(string='Generated Payment Files', readonly=True, default=0)
    
    # Payment Reconciliation Counts
    total_payment_reconciliations = fields.Integer(string='Payment Reconciliations', readonly=True, default=0)
    draft_reconciliations = fields.Integer(string='Draft Reconciliations', readonly=True, default=0)
    processed_reconciliations = fields.Integer(string='Processed Reconciliations', readonly=True, default=0)
    completed_reconciliations = fields.Integer(string='Completed Reconciliations', readonly=True, default=0)
    
    # Document Vault Counts
    total_documents = fields.Integer(string='Total Documents', readonly=True, default=0)
    
    # Active Mobile Users (based on JWT tokens)
    active_mobile_users = fields.Integer(string='Active Mobile Users', readonly=True, default=0,
                                        help='Number of unique users currently logged in via mobile channel')

    def _compute_all_counts(self):
        """Compute all counts for the dashboard"""
        for record in self:
            # Master Data Counts
            record.total_districts = self.env['bhu.district'].search_count([])
            record.total_sub_divisions = self.env['bhu.sub.division'].search_count([])
            record.total_tehsils = self.env['bhu.tehsil'].search_count([])
            record.total_villages = self.env['bhu.village'].search_count([])
            record.total_projects = self.env['bhu.project'].search_count([])
            record.total_departments = self.env['bhu.department'].search_count([])
            record.total_landowners = self.env['bhu.landowner'].search_count([])
            record.total_rate_masters = self.env['bhu.rate.master'].search_count([])
            
            # Survey Counts
            record.total_surveys = self.env['bhu.survey'].search_count([])
            record.draft_surveys = self.env['bhu.survey'].search_count([('state', '=', 'draft')])
            record.submitted_surveys = self.env['bhu.survey'].search_count([('state', '=', 'submitted')])
            record.approved_surveys = self.env['bhu.survey'].search_count([('state', '=', 'approved')])
            record.rejected_surveys = self.env['bhu.survey'].search_count([('state', '=', 'rejected')])
            # Total Surveys Done = Approved + Rejected
            record.total_surveys_done = record.approved_surveys + record.rejected_surveys
            # Pending = Submitted + Rejected
            record.pending_surveys = record.submitted_surveys + record.rejected_surveys
            
            # Section 4 Notifications
            record.total_section4_notifications = self.env['bhu.section4.notification'].search_count([])
            record.draft_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'draft')])
            record.generated_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'generated')])
            record.signed_section4 = self.env['bhu.section4.notification'].search_count([('state', '=', 'signed')])
            
            # Section 11 Reports
            record.total_section11_reports = self.env['bhu.section11.preliminary.report'].search_count([])
            record.draft_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'draft')])
            record.generated_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'generated')])
            record.signed_section11 = self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'signed')])
            
            # Expert Committee Reports
            record.total_expert_committee_reports = self.env['bhu.expert.committee.report'].search_count([])
            
            # Section 15 Objections
            record.total_section15_objections = self.env['bhu.section15.objection'].search_count([])
            
            # Section 19 Notifications
            record.total_section19_notifications = self.env['bhu.section19.notification'].search_count([])
            record.draft_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'draft')])
            record.generated_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'generated')])
            record.signed_section19 = self.env['bhu.section19.notification'].search_count([('state', '=', 'signed')])
            
            # SIA Teams
            record.total_sia_teams = self.env['bhu.sia.team'].search_count([])
            record.draft_sia_teams = self.env['bhu.sia.team'].search_count([('state', '=', 'draft')])
            record.submitted_sia_teams = self.env['bhu.sia.team'].search_count([('state', '=', 'submitted')])
            record.approved_sia_teams = self.env['bhu.sia.team'].search_count([('state', '=', 'approved')])
            record.send_back_sia_teams = self.env['bhu.sia.team'].search_count([('state', '=', 'send_back')])
            
            # Payment Files
            record.total_payment_files = self.env['bhu.payment.file'].search_count([])
            record.draft_payment_files = self.env['bhu.payment.file'].search_count([('state', '=', 'draft')])
            record.generated_payment_files = self.env['bhu.payment.file'].search_count([('state', '=', 'generated')])
            
            # Payment Reconciliations
            record.total_payment_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([])
            record.draft_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'draft')])
            record.processed_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'processed')])
            record.completed_reconciliations = self.env['bhu.payment.reconciliation.bank'].search_count([('state', '=', 'completed')])
            
            # Document Vault
            record.total_documents = self.env['bhu.document.vault'].search_count([])
            
            # Active Mobile Users (unique users with JWT tokens from mobile channel)
            mobile_tokens = self.env['jwt.token'].search([('channel_type', '=', 'mobile')])
            unique_mobile_users = len(set(mobile_tokens.mapped('user_id').ids))
            record.active_mobile_users = unique_mobile_users
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to compute and cache counts immediately"""
        # Pre-compute all counts once
        counts = self._get_all_counts()
        
        # Apply computed values to all records
        for vals in vals_list:
            vals.update(counts)
        
        records = super().create(vals_list)
        # Ensure computed fields are computed
        for record in records:
            record._compute_current_datetime()
            record._compute_is_admin()
        return records
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to ensure values are computed if missing"""
        result = super().read(fields=fields, load=load)
        
        # If any record has zero values, refresh them
        for record_data in result:
            if record_data.get('total_districts', 0) == 0:
                # This record needs refreshing
                record = self.browse(record_data['id'])
                counts = self._get_all_counts()
                record.write(counts)
                # Re-read to get updated values
                result = super().read(fields=fields, load=load)
                break
        
        
        # Ensure computed fields are computed
        for record_data in result:
            record = self.browse(record_data['id'])
            record._compute_current_datetime()
            record._compute_is_admin()
        
        return result
    
    @api.model
    def _get_model_count_by_status(self, model_name, base_domain, status=None, state_field='state'):
        """Generic method to get count by status for any model
        Args:
            model_name: Model name (e.g., 'bhu.survey')
            base_domain: Base domain to filter by
            status: Status value, list of statuses, or None for total count
                   (e.g., 'approved', ['approved', 'rejected'], or None)
            state_field: Field name for state (default: 'state')
        Returns:
            int: Count of records matching the domain and status
        """
        if not base_domain:
            base_domain = []
        
        if status is None:
            # Return total count without status filter
            return self.env[model_name].search_count(base_domain)
        
        if isinstance(status, list):
            status_domain = [(state_field, 'in', status)]
        else:
            status_domain = [(state_field, '=', status)]
        
        return self.env[model_name].search_count(base_domain + status_domain)
    
    @api.model
    def _get_section_counts(self, model_name, base_domain, state_field='state', states=None):
        """Generic method to get all state counts for a section
        Args:
            model_name: Model name (e.g., 'bhu.section4.notification')
            base_domain: Base domain to filter by
            state_field: Field name for state (default: 'state')
            states: List of states to count (default: ['draft', 'submitted', 'approved', 'send_back'])
        Returns:
            dict: Dictionary with total and counts for each state
        """
        if states is None:
            states = ['draft', 'submitted', 'approved', 'send_back']
        
        if not base_domain:
            base_domain = []
        
        total = self.env[model_name].search_count(base_domain)
        counts = {}
        for state in states:
            counts[f'{state}'] = self._get_model_count_by_status(model_name, base_domain, state, state_field)
        
        return {
            'total': total,
            **counts
        }
    
    @api.model
    def _get_survey_counts(self, base_domain):
        """Get all survey counts with completion percentage
        Args:
            base_domain: Base domain to filter surveys (can be empty list for all)
        Returns:
            dict: Dictionary with all survey counts and completion percentage
        """
        if not base_domain:
            base_domain = []
        
        total = self._get_model_count_by_status('bhu.survey', base_domain, None)
        draft = self._get_model_count_by_status('bhu.survey', base_domain, 'draft')
        submitted = self._get_model_count_by_status('bhu.survey', base_domain, 'submitted')
        approved = self._get_model_count_by_status('bhu.survey', base_domain, 'approved')
        rejected = self._get_model_count_by_status('bhu.survey', base_domain, 'rejected')
        total_done = self._get_model_count_by_status('bhu.survey', base_domain, ['approved', 'rejected'])
        pending = self._get_model_count_by_status('bhu.survey', base_domain, ['submitted', 'rejected'])
        
        # Calculate completion percentage
        completion_percent = 0
        if total > 0:
            completion_percent = round((approved / total) * 100, 2)
        
        return {
            'total': total,
            'draft': draft,
            'submitted': submitted,
            'approved': approved,
            'rejected': rejected,
            'total_done': total_done,
            'pending': pending,
            'completion_percent': completion_percent,
        }
    
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
    
    def action_refresh(self):
        """Refresh dashboard data"""
        counts = self._get_all_counts()
        self.write(counts)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dashboard Refreshed',
                'message': 'Dashboard data has been updated.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def name_get(self):
        """Return a name for the dashboard"""
        return [(record.id, 'Dashboard') for record in self]
    
    
    @api.model
    def action_open_dashboard(self):
        """Open dashboard - reuses existing record or creates new one with cached values"""
        # Try to find existing dashboard record (transient models persist until server restart)
        dashboard = self.search([], limit=1, order='create_date desc')
        
        if not dashboard:
            # Create new dashboard with pre-computed values
            dashboard = self.create({})
            # Ensure computed fields are computed
            dashboard._compute_current_datetime()
            dashboard._compute_is_admin()
            # Force recompute
            dashboard.invalidate_recordset(['current_datetime', 'is_admin'])
            dashboard._compute_current_datetime()
            dashboard._compute_is_admin()
        else:
            # Always refresh values to ensure they're up-to-date, but do it efficiently
            # Check if any key field is 0, which might indicate stale data
            needs_refresh = (
                dashboard.total_districts == 0 and 
                dashboard.total_surveys == 0 and 
                dashboard.total_section4_notifications == 0 and
                dashboard.total_payment_files == 0 and
                dashboard.total_rate_masters == 0
            )
            if needs_refresh:
                counts = self._get_all_counts()
                dashboard.write(counts)
        
        # Ensure values are always present (double-check)
        if dashboard.total_districts == 0 or dashboard.total_rate_masters == 0:
            counts = self._get_all_counts()
            dashboard.write(counts)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'bhuarjan.dashboard',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'current',
            'context': {'create': False, 'delete': False},
        }
    
    @api.model
    def _get_action_dict(self, action_ref):
        """Helper method to get action dictionary with all required fields"""
        try:
            # Use sudo to bypass any access issues when reading the action
            # Read all fields to ensure we get the complete action
            action = action_ref.sudo().read([])[0]
            # Ensure action has required fields for Odoo 18
            if 'type' not in action:
                action['type'] = 'ir.actions.act_window'
            if 'target' not in action:
                action['target'] = 'current'
            # Ensure views is a list (Odoo 18 requirement)
            # views should be a list of tuples: [(view_id, mode), ...]
            if 'views' not in action or not action.get('views') or action.get('views') == False:
                # If views is missing, create it from view_mode
                view_mode = action.get('view_mode', 'list,form')
                if isinstance(view_mode, str):
                    view_mode = view_mode.split(',')
                action['views'] = [(False, mode.strip()) for mode in view_mode]
            elif isinstance(action.get('views'), list):
                # Ensure all views are tuples
                action['views'] = [
                    (v[0], v[1]) if isinstance(v, (list, tuple)) and len(v) >= 2 else (False, v if isinstance(v, str) else 'list')
                    for v in action['views']
                ]
            return action
        except Exception as e:
            _logger.error(f"Error reading action {action_ref.id}: {e}", exc_info=True)
            # Fallback: create action dynamically from action_ref
            view_mode = action_ref.view_mode or 'list,form'
            if isinstance(view_mode, str):
                view_mode = view_mode.split(',')
            return {
                'type': 'ir.actions.act_window',
                'name': action_ref.name or action_ref.xml_id.split('.')[-1].replace('_', ' ').title() if hasattr(action_ref, 'xml_id') else 'Action',
                'res_model': action_ref.res_model,
                'view_mode': ','.join(view_mode),
                'views': [(False, mode) for mode in view_mode],
                'target': 'current',
            }
    
    @api.model
    def action_open_districts(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_district')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_district: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Districts',
                'res_model': 'bhu.district',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_sub_divisions(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_sub_division')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_sub_division: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sub Divisions',
                'res_model': 'bhu.sub.division',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_tehsils(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_tehsil')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_tehsil: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tehsils',
                'res_model': 'bhu.tehsil',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_villages(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_village')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_village: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Villages',
                'res_model': 'bhu.village',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_projects(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_project')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_project: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Projects',
                'res_model': 'bhu.project',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_departments(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_department')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_department: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Departments',
                'res_model': 'bhu.department',
                'view_mode': 'list,form',
                'target': 'current',
            }
    
    @api.model
    def action_open_landowners(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_landowner')
            action = self._get_action_dict(action_ref)
            # Clear any default filters to prevent saved filters from auto-applying
            if 'context' not in action:
                action['context'] = {}
            action['context'].update({
                'search_default_district_id': False,
            })
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_landowner: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Landowners',
                'res_model': 'bhu.landowner',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_rate_masters(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_rate_master')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_rate_master: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Rate Masters',
                'res_model': 'bhu.rate.master',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Draft Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_rejected(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'rejected')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'rejected')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_submitted(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'submitted')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Submitted Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'submitted')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_approved(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'approved')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Approved Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'approved')],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_pending(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', 'in', ['submitted', 'rejected'])]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Pending Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', 'in', ['submitted', 'rejected'])],
                'target': 'current',
            }
    
    @api.model
    def action_open_surveys_done(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_bhu_survey')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', 'in', ['approved', 'rejected'])]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_bhu_survey: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Completed Surveys',
                'res_model': 'bhu.survey',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', 'in', ['approved', 'rejected'])],
                'target': 'current',
            }
    
    @api.model
    def action_open_expert_committee(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_expert_committee_report')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_expert_committee_report: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Expert Committee Reports',
                'res_model': 'bhu.expert.committee.report',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section4(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section4_notification')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section4_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 4 Notifications',
                'res_model': 'bhu.section4.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section11(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section11_preliminary_report')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section11_preliminary_report: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 11 Preliminary Reports',
                'res_model': 'bhu.section11.preliminary.report',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section15(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section15_objections')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section15_objections: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 15 Objections',
                'res_model': 'bhu.section15.objection',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_documents(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_document_vault')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_document_vault: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Document Vault',
                'res_model': 'bhu.document.vault',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section19(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section19_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Draft)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section19_generated(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'generated')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Generated)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'generated')],
                'target': 'current',
            }
    
    @api.model
    def action_open_section19_signed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_section19_notification')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'signed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_section19_notification: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Section 19 Notifications (Signed)',
                'res_model': 'bhu.section19.notification',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'signed')],
                'target': 'current',
            }
    
    @api.model
    def action_open_payment_files(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_payment_files_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files (Draft)',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    
    @api.model
    def action_open_payment_files_generated(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_file')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'generated')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_file: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Files (Generated)',
                'res_model': 'bhu.payment.file',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'generated')],
                'target': 'current',
            }
    
    @api.model
    def action_open_payment_reconciliations(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_reconciliations_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Draft)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    
    @api.model
    def action_open_reconciliations_processed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'processed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Processed)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'processed')],
                'target': 'current',
            }
    
    @api.model
    def action_open_reconciliations_completed(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_payment_reconciliation_bank')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'completed')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_payment_reconciliation_bank: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment Reconciliations (Completed)',
                'res_model': 'bhu.payment.reconciliation',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'completed')],
                'target': 'current',
            }
    
    @api.model
    def action_open_sia_teams(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            return self._get_action_dict(action_ref)
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    @api.model
    def action_open_sia_teams_draft(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'draft')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Draft)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'draft')],
                'target': 'current',
            }
    
    @api.model
    def action_open_sia_teams_submitted(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'submitted')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Submitted)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'submitted')],
                'target': 'current',
            }
    
    @api.model
    def action_open_sia_teams_approved(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'approved')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Approved)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'approved')],
                'target': 'current',
            }
    
    @api.model
    def action_open_sia_teams_send_back(self):
        try:
            action_ref = self.env.ref('bhuarjan.action_create_sia_team')
            action = self._get_action_dict(action_ref)
            action['domain'] = [('state', '=', 'send_back')]
            return action
        except Exception as e:
            _logger.error(f"Error getting action_create_sia_team: {e}", exc_info=True)
            return {
                'type': 'ir.actions.act_window',
                'name': 'SIA Teams (Sent Back)',
                'res_model': 'bhu.sia.team',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'send_back')],
                'target': 'current',
            }
    
    @api.model
    def action_open_mobile_users(self):
        """Open mobile users list (JWT tokens with mobile channel)"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Active Mobile Users',
            'res_model': 'jwt.token',
            'view_mode': 'list,form',
            'domain': [('channel_type', '=', 'mobile')],
            'context': {'search_default_group_by_user': 1},
        }
    
    @api.model
    def get_all_departments(self):
        """Get all departments for dropdown - merged from sdm_dashboard with SDM filtering"""
        user = self.env.user
        
        # Admin, system users, and collectors see all departments
        if (user.has_group('bhuarjan.group_bhuarjan_admin') or 
            user.has_group('base.group_system') or
            user.has_group('bhuarjan.group_bhuarjan_collector') or
            user.has_group('bhuarjan.group_bhuarjan_additional_collector')):
            # Show all departments for admin/system/collector users
            departments = self.env['bhu.department'].search([])
        else:
            # For SDM/Tehsildar users, only show departments where they have assigned projects
            assigned_projects = self.env['bhu.project'].search([
                '|',
                ('sdm_ids', 'in', [user.id]),
                ('tehsildar_ids', 'in', [user.id])
            ])
            
            if assigned_projects:
                # Get unique department IDs from assigned projects
                department_ids = assigned_projects.mapped('department_id').ids
                if department_ids:
                    departments = self.env['bhu.department'].search([('id', 'in', department_ids)])
                else:
                    # No departments found, return empty list
                    return []
            else:
                # No assigned projects, return empty list
                return []
        
        return departments.read(["id", "name"])
    
    @api.model
    def get_all_projects(self, department_id=None):
        """Get all projects for dropdown, optionally filtered by department and user's assigned projects"""
        user = self.env.user
        domain = []
        
        # Filter by user's assigned projects (if not admin)
        if not user.has_group('bhuarjan.group_bhuarjan_admin') and not user.has_group('base.group_system'):
            # Get user's assigned projects
            assigned_projects = self.env['bhu.project'].search([
                '|',
                ('sdm_ids', 'in', user.id),
                ('tehsildar_ids', 'in', user.id)
            ])
            if assigned_projects:
                domain.append(('id', 'in', assigned_projects.ids))
            else:
                # No assigned projects, return empty list
                return []
        
        # Filter by department if provided
        if department_id:
            if domain:
                domain = ['&', ('department_id', '=', department_id)] + domain
            else:
                domain = [('department_id', '=', department_id)]
        
        projects = self.env["bhu.project"].search(domain)
        return projects.read(["id", "name"])
    
    @api.model
    def get_villages_by_project(self, project_id):
        """Get villages for a specific project"""
        project = self.env["bhu.project"].browse(project_id)
        if not project.exists():
            return []
        # Get villages from project's Many2many relationship
        villages = project.village_ids
        return villages.read(["id", "name"])
    
    @api.model
    def get_department_user_department(self):
        """Get the department for department user - first from user's department_id field, then from assigned projects"""
        user = self.env.user
        _logger.info(f"Getting department for user: {user.id} ({user.name})")
        
        # Check if user has department_user group
        has_group = user.has_group('bhuarjan.group_bhuarjan_department_user')
        _logger.info(f"User has department_user group: {has_group}")
        
        if not has_group:
            _logger.warning(f"User {user.id} ({user.name}) does not have department_user group")
            return None
      
        if not user.bhu_department_id:
            return None
        
        
        dept_data = {
            'id': user.bhu_department_id.id,
            'name': user.bhu_department_id.name
        }
        
        return dept_data
    
    @api.model
    def get_department_user_projects(self, department_id=None):
        """Get mapped projects for department user, optionally filtered by department"""
        user = self.env.user
        _logger.info(f"Getting projects for department user: {user.id} ({user.name})")
        
        if not user.has_group('bhuarjan.group_bhuarjan_department_user'):
            _logger.warning(f"User {user.id} does not have department_user group")
            return []
  
        # Filter by department if provided
        if department_id:
            domain = [('department_id', '=', int(department_id))]
        
        projects = self.env['bhu.project'].search(domain)
        _logger.info(f"Found {len(projects)} projects for user {user.id}")
        
        # Read project data including department_id
        project_data = projects.read(["id", "name", "department_id"])
        
        # Log each project and its department
        for proj in project_data:
            dept_id = proj.get('department_id')
            if dept_id:
                dept_name = dept_id[1] if isinstance(dept_id, (list, tuple)) else 'Unknown'
                _logger.info(f"  Project: {proj['name']} (ID: {proj['id']}), Department: {dept_name}")
            else:
                _logger.warning(f"  Project: {proj['name']} (ID: {proj['id']}) has NO department")
        
        return project_data
    
    @api.model
    def get_dashboard_stats(self, filters=None):
        """Get dashboard statistics for OWL component
        Args:
            filters: dict with keys 'department_id', 'project_id', 'village_id' (all optional)
        """
        try:
            # Handle filters - can be None, empty dict, or dict with values
            if filters is None:
                filters = {}
            elif not isinstance(filters, dict):
                filters = {}
            
            # Extract filter values, converting to int if they exist
            department_id = None
            project_id = None
            village_id = None
            
            if filters.get('department_id'):
                try:
                    department_id = int(filters.get('department_id'))
                except (ValueError, TypeError):
                    department_id = None
            
            if filters.get('project_id'):
                try:
                    project_id = int(filters.get('project_id'))
                except (ValueError, TypeError):
                    project_id = None
            
            if filters.get('village_id'):
                try:
                    village_id = int(filters.get('village_id'))
                except (ValueError, TypeError):
                    village_id = None
            
            counts = self._get_all_counts(project_id=project_id, village_id=village_id, department_id=department_id)
            return counts
        except Exception as e:
            import traceback
            _logger = logging.getLogger(__name__)
            _logger.error("Error in get_dashboard_stats: %s\n%s", str(e), traceback.format_exc())
            # Return empty counts on error
            return self._get_all_counts(project_id=None, village_id=None, department_id=None)
    
    @api.model
    def get_role_based_dashboard_action(self):
        """Return the appropriate dashboard action based on user role"""
        user = self.env.user
        # Check user roles in priority order
        is_admin = user.has_group('bhuarjan.group_bhuarjan_admin') or user.has_group('base.group_system')
        is_collector = user.has_group('bhuarjan.group_bhuarjan_collector') or user.has_group('bhuarjan.group_bhuarjan_additional_collector')
        is_department = user.has_group('bhuarjan.group_bhuarjan_department_user')
        is_sdm = user.has_group('bhuarjan.group_bhuarjan_sdm')
        
        # Use sudo() to bypass permission checks when reading action references
        if is_admin:
            # Return Admin Dashboard action
            action_ref = self.env.ref('bhuarjan.action_admin_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.admin_dashboard'
            name = 'Admin Dashboard'
        elif is_collector:
            # Return Collector Dashboard action
            action_ref = self.env.ref('bhuarjan.action_collector_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.collector_dashboard'
            name = 'Collector Dashboard'
        elif is_department:
            # Return Department User Dashboard action
            action_ref = self.env.ref('bhuarjan.action_department_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.department_dashboard'
            name = 'Department User Dashboard'
        elif is_sdm:
            # Return SDM Dashboard action
            action_ref = self.env.ref('bhuarjan.action_sdm_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.sdm_dashboard_tag'
            name = 'SDM Dashboard'
        else:
            # Fallback to SDM dashboard for other users
            action_ref = self.env.ref('bhuarjan.action_sdm_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.sdm_dashboard_tag'
            name = 'SDM Dashboard'
        
        if not action_ref:
            # Fallback to admin dashboard if action not found
            action_ref = self.env.ref('bhuarjan.action_admin_dashboard_owl', raise_if_not_found=False)
            tag = 'bhuarjan.admin_dashboard'
            name = 'Admin Dashboard'
        
        # Return a proper client action dictionary instead of reading the record
        # This avoids issues with action IDs that don't exist
        return {
            'type': 'ir.actions.client',
            'tag': tag,
            'name': name,
        }
    
    # ========== SDM Dashboard Methods (merged from sdm_dashboard.py) ==========
    
    @api.model
    def get_all_projects_sdm(self):
        """Get projects for current user (SDM) - merged from sdm_dashboard"""
        if self.env.user.has_group('bhuarjan.group_bhuarjan_sdm'):
            projects = self.env['bhu.project'].search([
                ('sdm_ids', 'in', [self.env.user.id])
            ])
        else:
            projects = self.env['bhu.project'].search([])

        return [{
            "id": p.id,
            "name": p.name
        } for p in projects]
    
    @api.model
    def get_all_projects_sdm_filtered(self, department_id=None):
        """Get projects for current user (SDM or Tehsildar), optionally filtered by department - merged from sdm_dashboard"""
        user = self.env.user
        domain = []
        
        # Admin, system users, and collectors see all projects
        if (user.has_group('bhuarjan.group_bhuarjan_admin') or 
            user.has_group('base.group_system') or
            user.has_group('bhuarjan.group_bhuarjan_collector') or
            user.has_group('bhuarjan.group_bhuarjan_additional_collector')):
            # Show all projects for admin/system/collector users
            if department_id:
                domain = [('department_id', '=', department_id)]
            projects = self.env['bhu.project'].search(domain)
        else:
            # For other users (SDM/Tehsildar), filter by assigned projects
            assigned_projects = self.env['bhu.project'].search([
                '|',
                ('sdm_ids', 'in', [user.id]),
                ('tehsildar_ids', 'in', [user.id])
            ])
            
            if assigned_projects:
                domain = [('id', 'in', assigned_projects.ids)]
                if department_id:
                    domain = ['&', ('department_id', '=', department_id)] + domain
                projects = self.env['bhu.project'].search(domain)
            else:
                # No assigned projects, return empty list
                return []
        
        return projects.read(["id", "name"])
    
    @api.model
    def get_villages_by_project_sdm(self, project_id):
        """Get villages for a specific project - merged from sdm_dashboard"""
        project = self.env["bhu.project"].browse(project_id)
        if not project.exists():
            return []
        villages = project.village_ids
        return villages.read(["id", "name"])
    
    @api.model
    def is_collector_user(self):
        """Check if current user is Collector - merged from sdm_dashboard"""
        return self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or \
               self.env.user.has_group('bhuarjan.group_bhuarjan_additional_collector') or \
               self.env.user.has_group('bhuarjan.group_bhuarjan_admin') or \
               self.env.user.has_group('base.group_system')
    
    @api.model
    def get_sdm_dashboard_stats(self, department_id=None, project_id=None, village_id=None):
        """Get dashboard statistics for SDM/Collector filtered by assigned projects - merged from sdm_dashboard"""
        try:
            user = self.env.user
            
            # Build domain filters
            project_domain = []
            village_domain = []
            
            # Get user's assigned projects (for SDM/Tehsildar) or all projects (for admin/collector)
            if (user.has_group('bhuarjan.group_bhuarjan_admin') or 
                user.has_group('base.group_system') or
                user.has_group('bhuarjan.group_bhuarjan_collector') or
                user.has_group('bhuarjan.group_bhuarjan_additional_collector')):
                # Admin/Collector: can see all projects (no project restriction)
                project_ids = None  # None means no filtering needed
            elif user.has_group('bhuarjan.group_bhuarjan_sdm'):
                # SDM: only assigned projects
                assigned_projects = self.env['bhu.project'].search([
                    ('sdm_ids', 'in', [user.id])
                ])
                project_ids = assigned_projects.ids
            else:
                # Tehsildar or other: assigned projects
                assigned_projects = self.env['bhu.project'].search([
                    '|',
                    ('sdm_ids', 'in', [user.id]),
                    ('tehsildar_ids', 'in', [user.id])
                ])
                project_ids = assigned_projects.ids if assigned_projects else []
            
            # Build project domain
            if project_ids is not None:  # User has project restrictions (SDM/Tehsildar)
                if project_ids:  # Has assigned projects
                    # Filter by department if provided
                    if department_id and not project_id:
                        dept_projects = self.env['bhu.project'].search([
                            ('department_id', '=', department_id),
                            ('id', 'in', project_ids)
                        ])
                        if dept_projects:
                            project_domain = [('project_id', 'in', dept_projects.ids)]
                        else:
                            project_domain = [('project_id', '=', False)]
                    elif project_id:
                        # If specific project is selected, filter by it
                        if project_id in project_ids:
                            project_domain = [('project_id', '=', project_id)]
                        else:
                            project_domain = [('project_id', '=', False)]
                    else:
                        # Filter by all assigned projects
                        project_domain = [('project_id', 'in', project_ids)]
                else:
                    # No assigned projects, return empty domain
                    project_domain = [('project_id', '=', False)]
            else:
                # Admin/Collector: no project restrictions, but can filter by department/project
                if department_id and not project_id:
                    # Filter by department - need to get projects in that department
                    dept_projects = self.env['bhu.project'].search([
                        ('department_id', '=', department_id)
                    ])
                    if dept_projects:
                        project_domain = [('project_id', 'in', dept_projects.ids)]
                    else:
                        project_domain = [('project_id', '=', False)]
                elif project_id:
                    project_domain = [('project_id', '=', project_id)]
                # else: no project domain filter (show all)
            
            # Filter by village if provided
            if village_id:
                village_domain = [('village_id', '=', village_id)]
            
            # Combine domains
            if project_domain:
                final_domain = project_domain + village_domain if village_domain else project_domain
            elif village_domain:
                final_domain = village_domain
            else:
                final_domain = []  # No filters - show all (for admin/collector)

            # Helper function to get first pending document and check if all approved
            def get_section_info(model_name, domain, state_field='state', is_survey=False):
                records = self.env[model_name].search(domain, order='create_date asc')
                total = len(records)
                submitted = records.filtered(lambda r: getattr(r, state_field, False) == 'submitted')
                approved = records.filtered(lambda r: getattr(r, state_field, False) == 'approved')
                rejected = records.filtered(lambda r: getattr(r, state_field, False) == 'rejected')
                send_back = records.filtered(lambda r: getattr(r, state_field, False) == 'send_back')
                draft = records.filtered(lambda r: getattr(r, state_field, False) == 'draft')
                all_approved = total > 0 and len(approved) == total
                
                # For surveys: completed if all are approved OR rejected (no pending/submitted/draft)
                # For other sections: completed if all are approved
                if is_survey:
                    is_completed = total > 0 and len(submitted) == 0 and len(draft) == 0 and (len(approved) + len(rejected) == total)
                else:
                    is_completed = all_approved
                
                first_pending = submitted[0] if submitted else False
                first_document = records[0] if records else False
                return {
                    'total': total,
                    'draft_count': len(draft),
                    'submitted_count': len(submitted),
                    'approved_count': len(approved),
                    'rejected_count': len(rejected),
                    'send_back_count': len(send_back),
                    'all_approved': all_approved,
                    'is_completed': is_completed,
                    'first_pending_id': first_pending.id if first_pending else False,
                    'first_document_id': first_document.id if first_document else False,
                }

            is_collector = self.is_collector_user()
            
            # Extract project IDs from domain/filters to calculate village-based completion
            project_ids_from_domain = []
            
            # First, try to get from explicit project_id parameter
            if project_id:
                project_ids_from_domain = [project_id]
            # Then try to extract from project_domain
            elif project_domain:
                # Extract project IDs from domain like [('project_id', 'in', [1, 2, 3])] or [('project_id', '=', 1)]
                for condition in project_domain:
                    if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                        field, operator, value = condition[0], condition[1], condition[2]
                        if field == 'project_id':
                            if operator == '=':
                                project_ids_from_domain = [value] if value else []
                            elif operator == 'in' and isinstance(value, list):
                                project_ids_from_domain = value
                            break
            # If still no project IDs, try department or user's assigned projects
            if not project_ids_from_domain:
                if department_id:
                    # Get all projects in the department
                    dept_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
                    project_ids_from_domain = dept_projects.ids
                else:
                    # Get all projects the user has access to
                    if project_ids is not None and project_ids:
                        project_ids_from_domain = project_ids
                    else:
                        # Admin/Collector: get all projects
                        all_projects = self.env['bhu.project'].search([])
                        project_ids_from_domain = all_projects.ids
            
            # Get total villages in the projects (unique villages across all projects)
            if project_ids_from_domain:
                projects = self.env['bhu.project'].browse(project_ids_from_domain)
                all_village_ids = []
                for project in projects:
                    all_village_ids.extend(project.village_ids.ids)
                total_villages = len(set(all_village_ids))
            else:
                total_villages = 0
            
            # Calculate completion percentages
            def calculate_completion_percentage(approved, rejected, total, is_survey=False):
                """Calculate completion percentage. For surveys: (approved + rejected) / total, for others: approved / total"""
                if total == 0:
                    return 0.0
                if is_survey:
                    return round(((approved + rejected) / total) * 100, 1)
                else:
                    return round((approved / total) * 100, 1)
            
            def calculate_village_based_completion(model_name, project_ids_list, state_field='state', approved_state='approved'):
                """Calculate completion based on villages with approved notifications vs total villages in project"""
                if not project_ids_list or total_villages == 0:
                    return 0.0
                
                # Get all approved notifications for the projects
                approved_notifications = self.env[model_name].search([
                    ('project_id', 'in', project_ids_list),
                    (state_field, '=', approved_state)
                ])
                
                # Get unique villages that have approved notifications
                villages_with_approved = set(approved_notifications.mapped('village_id').ids)
                
                # Calculate percentage: villages with approved / total villages
                return round((len(villages_with_approved) / total_villages) * 100, 1) if total_villages > 0 else 0.0
            
            # Create model-specific domains (some models don't have village_id field)
            # Models WITH village_id: survey, section4, section11, section15, section19
            # Models WITHOUT village_id: expert_committee_report, sia_team, draft_award
            domain_with_village = final_domain  # Includes village_id if provided
            domain_without_village = project_domain if project_domain else []  # Only project filter, no village
            
            # Get counts using generic methods
            survey_counts = self._get_survey_counts(domain_with_village)
            section4_counts = self._get_section_counts('bhu.section4.notification', domain_with_village)
            section11_counts = self._get_section_counts('bhu.section11.preliminary.report', domain_with_village)
            section15_counts = self._get_section_counts('bhu.section15.objection', domain_with_village)
            section19_counts = self._get_section_counts('bhu.section19.notification', domain_with_village)
            expert_counts = self._get_section_counts('bhu.expert.committee.report', domain_without_village)
            sia_counts = self._get_section_counts('bhu.sia.team', domain_without_village)
            
            # Draft Award uses 'signed' state instead of 'approved'
            draft_award_total = self._get_model_count_by_status('bhu.draft.award', domain_without_village, None, 'state')
            draft_award_approved = self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'signed', 'state')
            
            # Get project exemption status if a specific project is selected
            is_project_exempt = False
            if project_id:
                project = self.env['bhu.project'].browse(project_id)
                if project.exists():
                    is_project_exempt = project.is_sia_exempt or False
            
            return {
                'is_collector': is_collector,
                'is_project_exempt': is_project_exempt,
                # Surveys - using generic method
                'survey_total': survey_counts['total'],
                'survey_draft': survey_counts['draft'],
                'survey_submitted': survey_counts['submitted'],
                'survey_approved': survey_counts['approved'],
                'survey_rejected': survey_counts['rejected'],
                'survey_completion_percent': survey_counts['completion_percent'],
                'survey_info': get_section_info('bhu.survey', final_domain, 'state', is_survey=True),
                
                # Section 4 Notifications - using generic method
                'section4_total': section4_counts['total'],
                'section4_draft': section4_counts['draft'],
                'section4_submitted': section4_counts['submitted'],
                'section4_approved': section4_counts['approved'],
                'section4_send_back': section4_counts['send_back'],
                'section4_completion_percent': calculate_village_based_completion('bhu.section4.notification', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section4_info': get_section_info('bhu.section4.notification', final_domain),
                
                # Section 11 Reports - using generic method
                'section11_total': section11_counts['total'],
                'section11_draft': section11_counts['draft'],
                'section11_submitted': section11_counts['submitted'],
                'section11_approved': section11_counts['approved'],
                'section11_send_back': section11_counts['send_back'],
                'section11_completion_percent': calculate_village_based_completion('bhu.section11.preliminary.report', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section11_info': get_section_info('bhu.section11.preliminary.report', final_domain),
                
                # Section 15 Objections - using generic method
                'section15_total': section15_counts['total'],
                'section15_draft': section15_counts['draft'],
                'section15_submitted': section15_counts['submitted'],
                'section15_approved': section15_counts['approved'],
                'section15_send_back': section15_counts['send_back'],
                'section15_completion_percent': calculate_completion_percentage(section15_counts['approved'], 0, section15_counts['total'], is_survey=False),
                'section15_info': get_section_info('bhu.section15.objection', final_domain),
                
                # Section 19 Notifications - using generic method
                'section19_total': section19_counts['total'],
                'section19_draft': section19_counts['draft'],
                'section19_submitted': section19_counts['submitted'],
                'section19_approved': section19_counts['approved'],
                'section19_send_back': section19_counts['send_back'],
                'section19_completion_percent': calculate_village_based_completion('bhu.section19.notification', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section19_info': get_section_info('bhu.section19.notification', final_domain),
                
                # Expert Committee Reports - using generic method
                'expert_total': expert_counts['total'],
                'expert_draft': expert_counts['draft'],
                'expert_submitted': expert_counts['submitted'],
                'expert_approved': expert_counts['approved'],
                'expert_send_back': expert_counts['send_back'],
                'expert_completion_percent': calculate_completion_percentage(expert_counts['approved'], 0, expert_counts['total'], is_survey=False),
                'expert_info': get_section_info('bhu.expert.committee.report', final_domain),
                
                # SIA Teams - using generic method
                'sia_total': sia_counts['total'],
                'sia_draft': sia_counts['draft'],
                'sia_submitted': sia_counts['submitted'],
                'sia_approved': sia_counts['approved'],
                'sia_send_back': sia_counts['send_back'],
                'sia_completion_percent': calculate_completion_percentage(sia_counts['approved'], 0, sia_counts['total'], is_survey=False),
                'sia_info': get_section_info('bhu.sia.team', final_domain),
                
                # Draft Award - State wise (uses 'signed' state instead of 'approved')
                'draft_award_total': draft_award_total,
                'draft_award_draft': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'draft'),
                'draft_award_generated': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'generated'),
                'draft_award_approved': draft_award_approved,  # 'signed' state
                'draft_award_completion_percent': calculate_completion_percentage(draft_award_approved, 0, draft_award_total, is_survey=False),
                'draft_award_info': {
                    'total': draft_award_total,
                    'submitted_count': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'generated'),
                    'approved_count': draft_award_approved,
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': draft_award_total > 0 and draft_award_approved == draft_award_total,
                    'is_completed': draft_award_total > 0 and draft_award_approved == draft_award_total,
                    'first_pending_id': False,
                    'first_document_id': False,
                },
            }
        except Exception as e:
            _logger.error(f"Error getting SDM dashboard stats: {e}", exc_info=True)
            # Return zeros on error
            is_collector = self.is_collector_user()
            return {
                'is_collector': is_collector,
                'is_project_exempt': False,
                'survey_total': 0, 'survey_draft': 0, 'survey_submitted': 0, 'survey_approved': 0, 'survey_rejected': 0,
                'survey_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'section4_total': 0, 'section4_draft': 0, 'section4_submitted': 0, 'section4_approved': 0, 'section4_send_back': 0,
                'section4_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'section11_total': 0, 'section11_draft': 0, 'section11_submitted': 0, 'section11_approved': 0, 'section11_send_back': 0,
                'section11_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'section15_total': 0, 'section15_draft': 0, 'section15_submitted': 0, 'section15_approved': 0, 'section15_send_back': 0,
                'section15_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'section19_total': 0, 'section19_draft': 0, 'section19_submitted': 0, 'section19_approved': 0, 'section19_send_back': 0,
                'section19_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'expert_total': 0, 'expert_draft': 0, 'expert_submitted': 0, 'expert_approved': 0, 'expert_send_back': 0,
                'expert_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'sia_total': 0, 'sia_draft': 0, 'sia_submitted': 0, 'sia_approved': 0, 'sia_send_back': 0,
                'sia_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
                'draft_award_total': 0, 'draft_award_draft': 0, 'draft_award_generated': 0, 'draft_award_approved': 0,
                'draft_award_completion_percent': 0,
                'draft_award_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0, 'send_back_count': 0, 'all_approved': True, 'is_completed': True, 'first_pending_id': False, 'first_document_id': False},
            }

