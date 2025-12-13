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
    def _get_all_counts(self, project_id=None, village_id=None, department_id=None):
        """Get all counts - cached computation"""
        # Build domain filters
        project_domain = [('project_id', '=', project_id)] if project_id else []
        village_domain = [('village_id', '=', village_id)] if village_id else []
        
        # If department is selected but no project, filter projects by department
        if department_id and not project_id:
            department_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
            if department_projects:
                project_ids = department_projects.ids
                project_domain = [('project_id', 'in', project_ids)]
            else:
                # No projects for this department, return zeros for project-related counts
                project_domain = [('project_id', '=', False)]  # This will return 0 results
        
        # Base domains for sections - always create, but empty if no filters
        section4_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        section11_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        section19_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        section15_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        expert_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        sia_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        
        # Survey domain - filter by project/village if provided
        survey_base = project_domain + village_domain if (project_id or village_id or department_id) else []
        
        # Filter projects count by department if provided
        project_count_domain = []
        if department_id:
            project_count_domain = [('department_id', '=', department_id)]
        
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
            
            # Survey Counts - with filtering
            'total_surveys': self.env['bhu.survey'].search_count(survey_base),
            'draft_surveys': self.env['bhu.survey'].search_count(survey_base + [('state', '=', 'draft')]),
            'submitted_surveys': self.env['bhu.survey'].search_count(survey_base + [('state', '=', 'submitted')]),
            'approved_surveys': self.env['bhu.survey'].search_count(survey_base + [('state', '=', 'approved')]),
            'rejected_surveys': self.env['bhu.survey'].search_count(survey_base + [('state', '=', 'rejected')]),
            'total_surveys_done': self.env['bhu.survey'].search_count(survey_base + [('state', 'in', ['approved', 'rejected'])]),
            'pending_surveys': self.env['bhu.survey'].search_count(survey_base + [('state', 'in', ['submitted', 'rejected'])]),
            
            # Section 4 Notifications - State wise (filter by project/village if provided)
            'section4_total': self.env['bhu.section4.notification'].search_count(section4_base),
            'section4_draft': self.env['bhu.section4.notification'].search_count(section4_base + [('state', '=', 'draft')]),
            'section4_submitted': self.env['bhu.section4.notification'].search_count(section4_base + [('state', '=', 'submitted')]),
            'section4_approved': self.env['bhu.section4.notification'].search_count(section4_base + [('state', '=', 'approved')]),
            'section4_send_back': self.env['bhu.section4.notification'].search_count(section4_base + [('state', '=', 'send_back')]),
            
            # Section 11 Reports - State wise
            'section11_total': self.env['bhu.section11.preliminary.report'].search_count(section11_base),
            'section11_draft': self.env['bhu.section11.preliminary.report'].search_count(section11_base + [('state', '=', 'draft')]),
            'section11_submitted': self.env['bhu.section11.preliminary.report'].search_count(section11_base + [('state', '=', 'submitted')]),
            'section11_approved': self.env['bhu.section11.preliminary.report'].search_count(section11_base + [('state', '=', 'approved')]),
            'section11_send_back': self.env['bhu.section11.preliminary.report'].search_count(section11_base + [('state', '=', 'send_back')]),
            
            # Section 19 Notifications - State wise
            'section19_total': self.env['bhu.section19.notification'].search_count(section19_base),
            'section19_draft': self.env['bhu.section19.notification'].search_count(section19_base + [('state', '=', 'draft')]),
            'section19_submitted': self.env['bhu.section19.notification'].search_count(section19_base + [('state', '=', 'submitted')]),
            'section19_approved': self.env['bhu.section19.notification'].search_count(section19_base + [('state', '=', 'approved')]),
            'section19_send_back': self.env['bhu.section19.notification'].search_count(section19_base + [('state', '=', 'send_back')]),
            
            # Section 15 Objections - State wise
            'section15_total': self.env['bhu.section15.objection'].search_count(section15_base),
            'section15_draft': self.env['bhu.section15.objection'].search_count(section15_base + [('state', '=', 'draft')]),
            'section15_submitted': self.env['bhu.section15.objection'].search_count(section15_base + [('state', '=', 'submitted')]),
            'section15_approved': self.env['bhu.section15.objection'].search_count(section15_base + [('state', '=', 'approved')]),
            'section15_send_back': self.env['bhu.section15.objection'].search_count(section15_base + [('state', '=', 'send_back')]),
            
            # Expert Committee Reports - State wise
            'expert_committee_total': self.env['bhu.expert.committee.report'].search_count(expert_base),
            'expert_committee_draft': self.env['bhu.expert.committee.report'].search_count(expert_base + [('state', '=', 'draft')]),
            'expert_committee_submitted': self.env['bhu.expert.committee.report'].search_count(expert_base + [('state', '=', 'submitted')]),
            'expert_committee_approved': self.env['bhu.expert.committee.report'].search_count(expert_base + [('state', '=', 'approved')]),
            'expert_committee_send_back': self.env['bhu.expert.committee.report'].search_count(expert_base + [('state', '=', 'send_back')]),
            
            # SIA Teams - State wise
            'sia_total': self.env['bhu.sia.team'].search_count(sia_base),
            'sia_draft': self.env['bhu.sia.team'].search_count(sia_base + [('state', '=', 'draft')]),
            'sia_submitted': self.env['bhu.sia.team'].search_count(sia_base + [('state', '=', 'submitted')]),
            'sia_approved': self.env['bhu.sia.team'].search_count(sia_base + [('state', '=', 'approved')]),
            'sia_send_back': self.env['bhu.sia.team'].search_count(sia_base + [('state', '=', 'send_back')]),
            
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
            
            # Section 4 Notifications - State wise
            'section4_total': self.env['bhu.section4.notification'].search_count([]),
            'section4_draft': self.env['bhu.section4.notification'].search_count([('state', '=', 'draft')]),
            'section4_submitted': self.env['bhu.section4.notification'].search_count([('state', '=', 'submitted')]),
            'section4_approved': self.env['bhu.section4.notification'].search_count([('state', '=', 'approved')]),
            'section4_send_back': self.env['bhu.section4.notification'].search_count([('state', '=', 'send_back')]),
            
            # Section 11 Reports - State wise
            'section11_total': self.env['bhu.section11.preliminary.report'].search_count([]),
            'section11_draft': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'draft')]),
            'section11_submitted': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'submitted')]),
            'section11_approved': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'approved')]),
            'section11_send_back': self.env['bhu.section11.preliminary.report'].search_count([('state', '=', 'send_back')]),
            
            # Section 19 Notifications - State wise
            'section19_total': self.env['bhu.section19.notification'].search_count([]),
            'section19_draft': self.env['bhu.section19.notification'].search_count([('state', '=', 'draft')]),
            'section19_submitted': self.env['bhu.section19.notification'].search_count([('state', '=', 'submitted')]),
            'section19_approved': self.env['bhu.section19.notification'].search_count([('state', '=', 'approved')]),
            'section19_send_back': self.env['bhu.section19.notification'].search_count([('state', '=', 'send_back')]),
            
            # Section 15 Objections - State wise
            'section15_total': self.env['bhu.section15.objection'].search_count([]),
            'section15_draft': self.env['bhu.section15.objection'].search_count([('state', '=', 'draft')]),
            'section15_submitted': self.env['bhu.section15.objection'].search_count([('state', '=', 'submitted')]),
            'section15_approved': self.env['bhu.section15.objection'].search_count([('state', '=', 'approved')]),
            'section15_send_back': self.env['bhu.section15.objection'].search_count([('state', '=', 'send_back')]),
            
            # Expert Committee Reports - State wise
            'expert_committee_total': self.env['bhu.expert.committee.report'].search_count([]),
            'expert_committee_draft': self.env['bhu.expert.committee.report'].search_count([('state', '=', 'draft')]),
            'expert_committee_submitted': self.env['bhu.expert.committee.report'].search_count([('state', '=', 'submitted')]),
            'expert_committee_approved': self.env['bhu.expert.committee.report'].search_count([('state', '=', 'approved')]),
            'expert_committee_send_back': self.env['bhu.expert.committee.report'].search_count([('state', '=', 'send_back')]),
            
            # SIA Teams - State wise (already have these)
            'sia_total': self.env['bhu.sia.team'].search_count([]),
            'sia_draft': self.env['bhu.sia.team'].search_count([('state', '=', 'draft')]),
            'sia_submitted': self.env['bhu.sia.team'].search_count([('state', '=', 'submitted')]),
            'sia_approved': self.env['bhu.sia.team'].search_count([('state', '=', 'approved')]),
            'sia_send_back': self.env['bhu.sia.team'].search_count([('state', '=', 'send_back')]),
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
        """Get all departments for dropdown"""
        departments = self.env["bhu.department"].search([])
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

