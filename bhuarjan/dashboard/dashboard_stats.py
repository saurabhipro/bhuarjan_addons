# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DashboardStats(models.AbstractModel):
    """Unified Dashboard Statistics - Handles all dashboard types (SDM, Collector, Admin, Department, etc.)"""
    _name = 'bhuarjan.dashboard.stats'
    _description = 'Dashboard Statistics Methods'

    # ========== CONFIGURATION: Dashboard Type Settings ==========
    # 
    # This configuration determines how different user roles access dashboard data.
    # Modify these groups to change which users can see all projects vs filtered projects.
    #
    # CONFIGURATION GUIDE:
    # 1. can_see_all_projects: Users in these groups can see ALL projects (no filtering)
    #    - Typically: Admin, System, Collector roles
    # 2. sdm_groups: Users in these groups see only their assigned projects (via sdm_ids)
    #    - Typically: SDM (Sub-Divisional Magistrate) role
    # 3. tehsildar_groups: Users in these groups see projects assigned via sdm_ids OR tehsildar_ids
    #    - Add tehsildar-specific groups here if needed
    # 4. department_groups: Users in these groups see projects based on their department
    #    - Typically: Department User role
    #
    # To add a new dashboard type:
    # 1. Add the user group to the appropriate list above
    # 2. Update _get_user_project_access() method if custom logic is needed
    # 3. The get_dashboard_stats() method will automatically handle the new type
    #
    DASHBOARD_CONFIG = {
        'can_see_all_projects': [
            'bhuarjan.group_bhuarjan_admin',           # Admin users
            'base.group_system',                        # System users
            'bhuarjan.group_bhuarjan_collector',       # Collector users
            'bhuarjan.group_bhuarjan_additional_collector',  # Additional Collector users
            'bhuarjan.group_bhuarjan_district_administrator',  # District Administrator users
            'bhuarjan.group_bhuarjan_department_user',  # Department users - can see all projects
        ],
        'sdm_groups': [
            'bhuarjan.group_bhuarjan_sdm',             # SDM users
        ],
        'tehsildar_groups': [
            'bhuarjan.group_bhuarjan_tahsildar',
        ],
        'department_groups': [
            'bhuarjan.group_bhuarjan_department_user',  # Department users
        ],
    }

    # Models that have village_id field (for filtering)
    MODELS_WITH_VILLAGE = [
        'bhu.survey',
        'bhu.section4.notification',
        'bhu.section11.preliminary.report',
        'bhu.section15.objection',
        'bhu.section19.notification',
        'bhu.section21.notification',
    ]

    # Models that don't have village_id field (only project filtering)
    MODELS_WITHOUT_VILLAGE = [
        'bhu.expert.committee.report',
        'bhu.sia.team',
    ]

    # ========== Helper Methods ==========

    @api.model
    def _get_user_project_access(self):
        """Determine what projects the current user can access based on their role
        
        Returns:
            dict: {
                'can_see_all': bool,  # True if user can see all projects
                'project_ids': list,   # List of project IDs us1er can access (None if can_see_all)
                'user_type': str,     # 'admin', 'collector', 'sdm', 'tehsildar', 'department', 'other'
            }
        """
        user = self.env.user
        config = self.DASHBOARD_CONFIG
        
        # Check if user can see all projects
        can_see_all = any(user.has_group(group) for group in config['can_see_all_projects'])
        
        if can_see_all:
            # Determine user type in priority order
            if user.has_group('bhuarjan.group_bhuarjan_admin') or user.has_group('base.group_system'):
                user_type = 'admin'
            elif user.has_group('bhuarjan.group_bhuarjan_department_user'):
                user_type = 'department'
            elif user.has_group('bhuarjan.group_bhuarjan_district_administrator'):
                user_type = 'district_admin'
            else:
                user_type = 'collector'
            
            return {
                'can_see_all': True,
                'project_ids': None,
                'user_type': user_type,
            }
        
        # Check if user is SDM
        if any(user.has_group(group) for group in config['sdm_groups']):
            assigned_projects = self.env['bhu.project'].search([
                ('sdm_ids', 'in', [user.id])
            ])
            return {
                'can_see_all': False,
                'project_ids': assigned_projects.ids,
                'user_type': 'sdm',
            }
        
        # Check if user is Tehsildar or has assigned projects
        assigned_projects = self.env['bhu.project'].search([
            '|',
            ('sdm_ids', 'in', [user.id]),
            ('tehsildar_ids', 'in', [user.id])
        ])
        
        if assigned_projects:
            return {
                'can_see_all': False,
                'project_ids': assigned_projects.ids,
                'user_type': 'tehsildar',
            }
        
        # Department user
        if any(user.has_group(group) for group in config['department_groups']):
            return {
                'can_see_all': False,
                'project_ids': [],  # Department users see projects based on their department
                'user_type': 'department',
            }
        
        return {
            'can_see_all': False,
            'project_ids': [],
            'user_type': 'other',
        }

    @api.model
    def _build_filter_domains(self, department_id=None, project_id=None, village_id=None):
        """Build filter domains based on user access and provided filters
        
        Args:
            department_id: Optional department ID to filter by
            project_id: Optional project ID to filter by
            village_id: Optional village ID to filter by
            
        Returns:
            dict: {
                'project_domain': list,      # Domain for project filtering
                'village_domain': list,      # Domain for village filtering
                'final_domain': list,        # Combined domain for models with village_id
                'domain_without_village': list,  # Domain for models without village_id
                'project_ids_from_domain': list,  # List of project IDs for completion calculations
            }
        """
        user_access = self._get_user_project_access()
        project_domain = []
        village_domain = []
        
        # Build project domain based on user access
        if user_access['can_see_all']:
            # Admin/Collector: can filter by department/project, but no restriction
            if project_id:
                # If project is explicitly selected, always filter by it (even if village is also selected)
                project_domain = [('project_id', '=', project_id)]
            elif department_id:
                # Filter by department if no specific project selected
                dept_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
                project_domain = [('project_id', 'in', dept_projects.ids)] if dept_projects else [('project_id', '=', False)]
            # else: no project domain filter (show all)
        else:
            # User has project restrictions
            project_ids = user_access['project_ids'] or []
            
            if project_ids:
                # User has assigned projects
                if department_id and not project_id:
                    # Filter by department within assigned projects
                    dept_projects = self.env['bhu.project'].search([
                        ('department_id', '=', department_id),
                        ('id', 'in', project_ids)
                    ])
                    project_domain = [('project_id', 'in', dept_projects.ids)] if dept_projects else [('project_id', '=', False)]
                elif project_id:
                    # Filter by specific project if user has access
                    project_domain = [('project_id', '=', project_id)] if project_id in project_ids else [('project_id', '=', False)]
                else:
                    # Filter by all assigned projects
                    project_domain = [('project_id', 'in', project_ids)]
            else:
                # No assigned projects
                project_domain = [('project_id', '=', False)]
        
        # Build village domain
        if village_id:
            village_domain = [('village_id', '=', village_id)]
        
        # Combine domains - IMPORTANT: Always combine project and village if both exist
        # CRITICAL: When village is selected, we MUST preserve project filter if project was selected
        # This ensures that when user selects a project, then selects a village, both filters apply
        
        # Log domain combination for debugging
        _logger.info(f"Domain Building - project_id={project_id}, village_id={village_id}, project_domain={project_domain}, village_domain={village_domain}")
        
        if project_domain and village_domain:
            # Both project and village filters - combine with AND (this is the expected case)
            final_domain = project_domain + village_domain
            _logger.info(f"Domain Building - Combined both: {final_domain}")
        elif project_domain:
            # Only project filter (no village selected)
            final_domain = project_domain
            _logger.info(f"Domain Building - Project only: {final_domain}")
        elif village_domain:
            # Only village filter (no project selected) - this should still work
            final_domain = village_domain
            _logger.info(f"Domain Building - Village only: {final_domain}")
        else:
            # No filters
            final_domain = []
            _logger.info(f"Domain Building - No filters")
        
        # Domain for models without village_id (only project filter, no village)
        # Ensure we use empty list if project_domain is empty or falsy
        domain_without_village = project_domain if project_domain else []
        _logger.info(f"Domain Building - domain_without_village for Section 8: {domain_without_village}")
        
        # Domain for models with village_ids M2M (Expert, SIA)
        # These models handle multiple villages, so we need to check if the filtered village is IN the record's villages
        m2m_village_domain = list(domain_without_village)  # Start with project filter
        if village_domain:
            # Extract village_id from domain [('village_id', '=', ID)]
            v_id = None
            for item in village_domain:
                if isinstance(item, (list, tuple)) and item[0] == 'village_id' and item[1] == '=':
                    v_id = item[2]
                    break
            
            if v_id:
                # Add M2M check for village
                m2m_village_domain.append(('village_ids', 'in', [v_id]))
        
        _logger.info(f"Domain Building - m2m_village_domain for Expert/SIA: {m2m_village_domain}")

        # Extract project IDs for completion calculations
        project_ids_from_domain = self._extract_project_ids(project_id, project_domain, department_id, user_access)
        
        return {
            'project_domain': project_domain,
            'village_domain': village_domain,
            'final_domain': final_domain,
            'domain_without_village': domain_without_village,
            'm2m_village_domain': m2m_village_domain,
            'project_ids_from_domain': project_ids_from_domain,
        }

    @api.model
    def _extract_project_ids(self, project_id, project_domain, department_id, user_access):
        """Extract project IDs from filters for completion calculations"""
        project_ids_from_domain = []
        
        if project_id:
            project_ids_from_domain = [project_id]
        elif project_domain:
            # Extract from domain like [('project_id', 'in', [1, 2, 3])] or [('project_id', '=', 1)]
            for condition in project_domain:
                if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                    field, operator, value = condition[0], condition[1], condition[2]
                    if field == 'project_id':
                        if operator == '=':
                            project_ids_from_domain = [value] if value else []
                        elif operator == 'in' and isinstance(value, list):
                            project_ids_from_domain = value
                        break
        
        if not project_ids_from_domain:
            if department_id:
                dept_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
                project_ids_from_domain = dept_projects.ids
            else:
                if user_access['project_ids'] is not None and user_access['project_ids']:
                    project_ids_from_domain = user_access['project_ids']
                else:
                    all_projects = self.env['bhu.project'].search([])
                    project_ids_from_domain = all_projects.ids
        
        return project_ids_from_domain

    @api.model
    def _get_section_info(self, model_name, domain, state_field='state', is_survey=False):
        """Get detailed section information including first pending document
        
        Args:
            model_name: Model name (e.g., 'bhu.survey')
            domain: Domain to filter records
            state_field: Field name for state (default: 'state')
            is_survey: Whether this is a survey (different completion logic)
            
        Returns:
            dict: Section information with counts and status
        """
        records = self.env[model_name].search(domain, order='create_date asc')
        total = len(records)
        
        submitted = records.filtered(lambda r: getattr(r, state_field, False) == 'submitted')
        approved = records.filtered(lambda r: getattr(r, state_field, False) == 'approved')
        rejected = records.filtered(lambda r: getattr(r, state_field, False) == 'rejected')
        send_back = records.filtered(lambda r: getattr(r, state_field, False) == 'send_back')
        draft = records.filtered(lambda r: getattr(r, state_field, False) == 'draft')
        
        all_approved = total > 0 and len(approved) == total
        
        # Completion logic: surveys need approved OR rejected, others need all approved
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

    @api.model
    def _calculate_completion_percentage(self, approved, rejected, total, is_survey=False):
        """Calculate completion percentage
        
        Args:
            approved: Number of approved items
            rejected: Number of rejected items
            total: Total number of items
            is_survey: Whether this is a survey (different calculation)
            
        Returns:
            float: Completion percentage (0-100)
        """
        if total == 0:
            return 0.0
        
        if is_survey:
            # For surveys: completion = (approved + rejected) / total
            # If all are approved or rejected, it's 100%
            completion = ((approved + rejected) / total) * 100
        else:
            # For other sections: completion = approved / total
            # If all are approved, it's 100%
            completion = (approved / total) * 100
        
        # Ensure it's between 0 and 100, and round to 1 decimal place
        completion = max(0.0, min(100.0, completion))
        return round(completion, 1)

    @api.model
    def _calculate_village_based_completion(self, model_name, project_ids_list, total_villages, state_field='state', approved_state='approved'):
        """Calculate completion based on villages with approved notifications vs total villages
        
        Args:
            model_name: Model name to check
            project_ids_list: List of project IDs
            total_villages: Total number of villages in projects
            state_field: Field name for state
            approved_state: State value for approved
            
        Returns:
            float: Completion percentage
        """
        if not project_ids_list or total_villages == 0:
            return 0.0
        
        approved_notifications = self.env[model_name].search([
            ('project_id', 'in', project_ids_list),
            (state_field, '=', approved_state)
        ])
        
        villages_with_approved = set(approved_notifications.mapped('village_id').ids)
        
        return round((len(villages_with_approved) / total_villages) * 100, 1) if total_villages > 0 else 0.0

    @api.model
    def _get_total_villages(self, project_ids_list):
        """Get total unique villages across projects"""
        if not project_ids_list:
            return 0
        
        projects = self.env['bhu.project'].browse(project_ids_list)
        all_village_ids = []
        for project in projects:
            all_village_ids.extend(project.village_ids.ids)
        
        return len(set(all_village_ids))

    @api.model
    def _get_all_section_counts(self, domains):
        """Get counts for all sections using generic methods
        
        Args:
            domains: dict with 'with_village' and 'without_village' domains
            
        Returns:
            dict: All section counts
        """
        domain_with_village = domains['final_domain']
        domain_without_village = domains['domain_without_village']
        m2m_village_domain = domains.get('m2m_village_domain', domain_without_village)  # Fallback just in case
        
        # Get counts using generic methods
        # Get counts using generic methods
        # Include 'generated' and 'signed' states for all workflow sections
        workflow_states = ['draft', 'submitted', 'approved', 'send_back', 'generated', 'signed']
        
        counts = {
            'survey': self._get_survey_counts(domain_with_village),
            'section4': self._get_section_counts('bhu.section4.notification', domain_with_village, states=workflow_states),
            'section11': self._get_section_counts('bhu.section11.preliminary.report', domain_with_village, states=workflow_states),
            'section15': self._get_section_counts('bhu.section15.objection', domain_with_village, states=workflow_states),
            'section19': self._get_section_counts('bhu.section19.notification', domain_with_village, states=workflow_states),
            'expert': self._get_section_counts('bhu.expert.committee.report', domain_without_village, states=workflow_states),
            'sia': self._get_section_counts('bhu.sia.team', domain_without_village, states=workflow_states),
            'section8': self._get_section_counts('bhu.section8', domain_without_village, state_field='state', states=['draft', 'approved', 'rejected']),  # Section 8 is per project, not per village
            # Railway Act Sections (all have village_id)
            # Sections 20A and 20E have no workflow - simple count only
            'section20a_railways': self._get_simple_section_counts('bhu.section20a.railways', domain_with_village),
            'section20d_railways': self._get_section_counts('bhu.section20d.railways', domain_with_village, states=workflow_states),
            'section20e_railways': self._get_simple_section_counts('bhu.section20e.railways', domain_with_village),
            # National Highway Act Sections (all have village_id)
            # Sections 3A and 3D have no workflow - simple count only
            'section3a_nh': self._get_simple_section_counts('bhu.section3a.nh', domain_with_village),
            'section3c_nh': self._get_section_counts('bhu.section3c.nh', domain_with_village, states=workflow_states),
            'section3d_nh': self._get_simple_section_counts('bhu.section3d.nh', domain_with_village),
            # Mutual Consent Policy (has village_id)
            'mutual_consent_policy': self._get_section_counts('bhu.mutual.consent.policy', domain_with_village, states=workflow_states),
            # Section 23 Award (has village_id)
            'section23_award': self._get_section_counts('bhu.section23.award', domain_with_village, states=workflow_states),
        }
        
        # Section 21 Notification uses standard workflow states (draft, submitted, approved, send_back)
        section21_total = self._get_model_count_by_status('bhu.section21.notification', domain_with_village, None)
        _logger.info(f"Section 21 counts - domain: {domain_with_village}, total: {section21_total}")
        counts['draft_award'] = {
            'total': section21_total,
            'approved': self._get_model_count_by_status('bhu.section21.notification', domain_with_village, 'approved'),
            'draft': self._get_model_count_by_status('bhu.section21.notification', domain_with_village, 'draft'),
            'submitted': self._get_model_count_by_status('bhu.section21.notification', domain_with_village, 'submitted'),
            'send_back': self._get_model_count_by_status('bhu.section21.notification', domain_with_village, 'send_back'),
        }
        
        # Log Section 23 Award counts
        section23_total = counts['section23_award']['total']
        _logger.info(f"Section 23 Award counts - domain: {domain_with_village}, total: {section23_total}")
        
        return counts

    # ========== Public API Methods ==========

    @api.model
    def is_collector_user(self):
        """Check if current user is Collector"""
        user = self.env.user
        return (user.has_group('bhuarjan.group_bhuarjan_collector') or
                user.has_group('bhuarjan.group_bhuarjan_additional_collector') or
                user.has_group('bhuarjan.group_bhuarjan_admin') or
                user.has_group('base.group_system'))

    @api.model
    def get_dashboard_stats(self, department_id=None, project_id=None, village_id=None, filters=None):
        """Get unified dashboard statistics for all dashboard types
        
        This method works for:
        - SDM Dashboard
        - Collector Dashboard
        - Admin Dashboard
        - Department Dashboard
        - District Admin Dashboard
        - Any other dashboard type
        
        Supports both calling styles:
        1. Individual parameters: get_dashboard_stats(department_id, project_id, village_id)
        2. Filters dict: get_dashboard_stats(filters={'department_id': 1, 'project_id': 2})
        
        Args:
            department_id: Optional department ID to filter by (if called with individual params)
            project_id: Optional project ID to filter by (if called with individual params)
            village_id: Optional village ID to filter by (if called with individual params)
            filters: Optional dict with keys 'department_id', 'project_id', 'village_id' (legacy style)
            
        Returns:
            dict: Complete dashboard statistics
        """
        try:
            # Handle both calling styles: individual params or filters dict
            if filters is not None and isinstance(filters, dict):
                # Legacy style: called with filters dict
                department_id = filters.get('department_id') or department_id
                project_id = filters.get('project_id') or project_id
                village_id = filters.get('village_id') or village_id
                # Convert to int if they exist
                if department_id:
                    try:
                        department_id = int(department_id)
                    except (ValueError, TypeError):
                        department_id = None
                if project_id:
                    try:
                        project_id = int(project_id)
                    except (ValueError, TypeError):
                        project_id = None
                if village_id:
                    try:
                        village_id = int(village_id)
                    except (ValueError, TypeError):
                        village_id = None
            
            # Build filter domains based on user access
            domains = self._build_filter_domains(department_id, project_id, village_id)
            
            # Log the filters and domains for debugging
            _logger.info(f"Dashboard Stats - Input Filters: department_id={department_id}, project_id={project_id}, village_id={village_id}")
            _logger.info(f"Dashboard Stats - Built Domains: project_domain={domains['project_domain']}, village_domain={domains['village_domain']}, final_domain={domains['final_domain']}")
            
            # Get user info
            user_access = self._get_user_project_access()
            is_collector = self.is_collector_user()
            _logger.info(f"Dashboard Stats - User access: can_see_all={user_access['can_see_all']}, user_type={user_access['user_type']}, project_ids={user_access['project_ids']}")
            
            # Debug: Test survey query directly
            if domains['final_domain']:
                test_surveys = self.env['bhu.survey'].search(domains['final_domain'], limit=10)
                _logger.info(f"Dashboard Stats - Test query found {len(test_surveys)} surveys with domain {domains['final_domain']}")
                if test_surveys:
                    _logger.info(f"Dashboard Stats - Sample survey IDs: {test_surveys.mapped('id')}")
            
            # Get project exemption status and allowed sections
            is_project_exempt = False
            is_displacement = False
            allowed_section_names = []  # List of section names allowed for this project
            if project_id:
                project = self.env['bhu.project'].browse(project_id)
                if project.exists():
                    is_project_exempt = project.is_sia_exempt or False
                    is_displacement = project.is_displacement or False
                    # Get sections from project's law
                    if project.law_master_id and project.law_master_id.section_ids:
                        allowed_section_names = project.law_master_id.section_ids.mapped('name')
                        _logger.info(f"Dashboard Stats - Project {project_id} has law '{project.law_master_id.name}' with sections: {allowed_section_names}")
            
            # Get total villages for completion calculations
            total_villages = self._get_total_villages(domains['project_ids_from_domain'])
            
            # Get all section counts
            counts = self._get_all_section_counts(domains)
            
            # Log survey counts for debugging
            # Log survey counts for debugging
            _logger.info(f"Dashboard Stats - Survey counts: total={counts['survey']['total']}, approved={counts['survey']['approved']}, domain={domains['final_domain']}")
            
            # Log Section 4 counts significantly
            try:
                _logger.info(f"Dashboard Stats - Section 4 counts: "
                             f"total={counts['section4']['total']},"
                             f"draft={counts['section4']['draft']},"
                             f"generated={counts['section4'].get('generated', 0)},"
                             f"submitted={counts['section4']['submitted']},"
                             f"Domain={domains['final_domain']}")
                if domains['final_domain']:
                    sec4_recs = self.env['bhu.section4.notification'].search(domains['final_domain'])
                    if sec4_recs:
                        _logger.info(f"Dashboard Stats - FOUND Section 4 IDs: {sec4_recs.ids}, States: {sec4_recs.mapped('state')}")
                    else:
                        _logger.info("Dashboard Stats - NO Section 4 records found with this domain.")
            except Exception as e:
                 _logger.error(f"Error logging section 4 stats: {e}")
            
            # Debug Section 8 specifically
            _logger.info(f"Dashboard Stats - Section 8 domain_without_village: {domains['domain_without_village']}")
            _logger.info(f"Dashboard Stats - Section 8 counts: total={counts.get('section8', {}).get('total', 0)}, draft={counts.get('section8', {}).get('draft', 0)}, approved={counts.get('section8', {}).get('approved', 0)}, rejected={counts.get('section8', {}).get('rejected', 0)}")
            # Test Section 8 query directly
            test_section8 = self.env['bhu.section8'].search(domains['domain_without_village'] if domains['domain_without_village'] else [])
            _logger.info(f"Dashboard Stats - Direct Section 8 query found {len(test_section8)} records with domain {domains['domain_without_village']}")
            if test_section8:
                _logger.info(f"Dashboard Stats - Section 8 record IDs: {test_section8.mapped('id')}, projects: {test_section8.mapped('project_id.id')}, states: {test_section8.mapped('state')}")
            
            # Debug: Test the domain directly to verify it's working
            if domains['final_domain']:
                test_surveys = self.env['bhu.survey'].search(domains['final_domain'], limit=10)
                test_count = len(test_surveys)
                _logger.info(f"Dashboard Stats - Direct test: Found {test_count} surveys with domain {domains['final_domain']}")
                if test_surveys:
                    _logger.info(f"Dashboard Stats - Sample survey IDs: {test_surveys.mapped('id')}, villages: {test_surveys.mapped('village_id.id')}")
                else:
                    # Try without village filter to see if project filter works
                    if domains['project_domain']:
                        test_without_village = self.env['bhu.survey'].search(domains['project_domain'], limit=10)
                        _logger.info(f"Dashboard Stats - Without village filter: Found {len(test_without_village)} surveys with project domain {domains['project_domain']}")
            
            # Build response with all statistics
            result = {
                'is_collector': is_collector,
                'is_project_exempt': is_project_exempt,
                'is_displacement': is_displacement,
                'user_type': user_access['user_type'],
                'allowed_section_names': allowed_section_names,  # Sections mapped to project's law
                
                # Surveys
                'survey_total': counts['survey']['total'],
                'survey_draft': counts['survey']['draft'],
                'survey_submitted': counts['survey']['submitted'],
                'survey_approved': counts['survey']['approved'],
                'survey_rejected': counts['survey']['rejected'],
                'survey_completion_percent': counts['survey']['completion_percent'],
                'survey_info': self._get_section_info('bhu.survey', domains['final_domain'], 'state', is_survey=True),
                
                # Section 4 (has village_id)
                'section4_total': counts['section4']['total'],
                'section4_draft': counts['section4']['draft'],
                'section4_submitted': counts['section4']['submitted'],
                'section4_approved': counts['section4']['approved'],
                'section4_send_back': counts['section4']['send_back'],
                'section4_generated': counts['section4'].get('generated', 0),
                'section4_signed': counts['section4'].get('signed', 0),
                'section4_completion_percent': self._calculate_village_based_completion(
                    'bhu.section4.notification', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section4_info': self._get_section_info('bhu.section4.notification', domains['final_domain']),
                
                # Section 11 (has village_id)
                'section11_total': counts['section11']['total'],
                'section11_draft': counts['section11']['draft'],
                'section11_submitted': counts['section11']['submitted'],
                'section11_approved': counts['section11']['approved'],
                'section11_send_back': counts['section11']['send_back'],
                'section11_generated': counts['section11'].get('generated', 0),
                'section11_signed': counts['section11'].get('signed', 0),
                'section11_completion_percent': self._calculate_village_based_completion(
                    'bhu.section11.preliminary.report', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section11_info': self._get_section_info('bhu.section11.preliminary.report', domains['final_domain']),
                
                # Section 15 (has village_id)
                'section15_total': counts['section15']['total'],
                'section15_draft': counts['section15']['draft'],
                'section15_submitted': counts['section15']['submitted'],
                'section15_approved': counts['section15']['approved'],
                'section15_send_back': counts['section15']['send_back'],
                'section15_completion_percent': self._calculate_completion_percentage(
                    counts['section15']['approved'], 0, counts['section15']['total'], is_survey=False
                ),
                'section15_info': self._get_section_info('bhu.section15.objection', domains['final_domain']),
                
                # Section 19 (has village_id)
                'section19_total': counts['section19']['total'],
                'section19_draft': counts['section19']['draft'],
                'section19_submitted': counts['section19']['submitted'],
                'section19_approved': counts['section19']['approved'],
                'section19_send_back': counts['section19']['send_back'],
                'section19_generated': counts['section19'].get('generated', 0),
                'section19_signed': counts['section19'].get('signed', 0),
                'section19_completion_percent': self._calculate_village_based_completion(
                    'bhu.section19.notification', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section19_info': self._get_section_info('bhu.section19.notification', domains['final_domain']),
                
                # Expert Committee (uses m2m_village_domain)
                'expert_total': counts['expert']['total'],
                'expert_draft': counts['expert']['draft'],
                'expert_submitted': counts['expert']['submitted'],
                'expert_approved': counts['expert']['approved'],
                'expert_send_back': counts['expert']['send_back'],
                'expert_completion_percent': self._calculate_completion_percentage(
                    counts['expert']['approved'], 0, counts['expert']['total'], is_survey=False
                ),
                'expert_info': self._get_section_info('bhu.expert.committee.report', domains['domain_without_village']),
                
                # SIA Teams (uses m2m_village_domain)
                'sia_total': counts['sia']['total'],
                'sia_draft': counts['sia']['draft'],
                'sia_submitted': counts['sia']['submitted'],
                'sia_approved': counts['sia']['approved'],
                'sia_send_back': counts['sia']['send_back'],
                'sia_completion_percent': self._calculate_completion_percentage(
                    counts['sia']['approved'], 0, counts['sia']['total'], is_survey=False
                ),
                'sia_info': self._get_section_info('bhu.sia.team', domains['domain_without_village']),
                
                # Section 8 (NO village_id - use domain_without_village, per project)
                'section8_total': counts['section8']['total'],
                'section8_draft': counts['section8']['draft'],
                'section8_approved': counts['section8']['approved'],
                'section8_rejected': counts['section8']['rejected'],
                'section8_completion_percent': self._calculate_completion_percentage(
                    counts['section8']['approved'], counts['section8']['rejected'], counts['section8']['total'], is_survey=False
                ),
                'section8_info': self._get_section_info('bhu.section8', domains['domain_without_village']),
                
                # Draft Award
                'draft_award_total': counts['draft_award']['total'],
                'draft_award_draft': counts['draft_award']['draft'],
                'draft_award_submitted': counts['draft_award']['submitted'],
                'draft_award_approved': counts['draft_award']['approved'],
                'draft_award_send_back': counts['draft_award']['send_back'],
                'draft_award_completion_percent': self._calculate_completion_percentage(
                    counts['draft_award']['approved'], 0, counts['draft_award']['total'], is_survey=False
                ),
                'draft_award_info': self._get_section_info('bhu.section21.notification', domains['final_domain']),
                
                # Railway Act Sections (all have village_id)
                # Section 20A - No workflow, just total count
                'section20a_railways_total': counts['section20a_railways']['total'],
                'section20a_railways_draft': 0,
                'section20a_railways_submitted': 0,
                'section20a_railways_approved': 0,
                'section20a_railways_send_back': 0,
                'section20a_railways_completion_percent': 0.0,
                'section20a_railways_info': {
                    'total': counts['section20a_railways']['total'],
                    'draft_count': 0,
                    'submitted_count': 0,
                    'approved_count': 0,
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': True,
                    'is_completed': True,
                    'first_pending_id': False,
                    'first_document_id': False,
                },
                
                'section20d_railways_total': counts['section20d_railways']['total'],
                'section20d_railways_draft': counts['section20d_railways']['draft'],
                'section20d_railways_submitted': counts['section20d_railways']['submitted'],
                'section20d_railways_approved': counts['section20d_railways']['approved'],
                'section20d_railways_send_back': counts['section20d_railways']['send_back'],
                'section20d_railways_completion_percent': self._calculate_completion_percentage(
                    counts['section20d_railways']['approved'], 0, counts['section20d_railways']['total'], is_survey=False
                ),
                'section20d_railways_info': self._get_section_info('bhu.section20d.railways', domains['final_domain']),
                
                # Section 20E - No workflow, just total count
                'section20e_railways_total': counts['section20e_railways']['total'],
                'section20e_railways_draft': 0,
                'section20e_railways_submitted': 0,
                'section20e_railways_approved': 0,
                'section20e_railways_send_back': 0,
                'section20e_railways_completion_percent': 0.0,
                'section20e_railways_info': {
                    'total': counts['section20e_railways']['total'],
                    'draft_count': 0,
                    'submitted_count': 0,
                    'approved_count': 0,
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': True,
                    'is_completed': True,
                    'first_pending_id': False,
                    'first_document_id': False,
                },
                
                # National Highway Act Sections (all have village_id)
                # Section 3A - No workflow, just total count
                'section3a_nh_total': counts['section3a_nh']['total'],
                'section3a_nh_draft': 0,
                'section3a_nh_submitted': 0,
                'section3a_nh_approved': 0,
                'section3a_nh_send_back': 0,
                'section3a_nh_completion_percent': 0.0,
                'section3a_nh_info': {
                    'total': counts['section3a_nh']['total'],
                    'draft_count': 0,
                    'submitted_count': 0,
                    'approved_count': 0,
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': True,
                    'is_completed': True,
                    'first_pending_id': False,
                    'first_document_id': False,
                },
                
                'section3c_nh_total': counts['section3c_nh']['total'],
                'section3c_nh_draft': counts['section3c_nh']['draft'],
                'section3c_nh_submitted': counts['section3c_nh']['submitted'],
                'section3c_nh_approved': counts['section3c_nh']['approved'],
                'section3c_nh_send_back': counts['section3c_nh']['send_back'],
                'section3c_nh_completion_percent': self._calculate_completion_percentage(
                    counts['section3c_nh']['approved'], 0, counts['section3c_nh']['total'], is_survey=False
                ),
                'section3c_nh_info': self._get_section_info('bhu.section3c.nh', domains['final_domain']),
                
                # Section 3D - No workflow, just total count
                'section3d_nh_total': counts['section3d_nh']['total'],
                'section3d_nh_draft': 0,
                'section3d_nh_submitted': 0,
                'section3d_nh_approved': 0,
                'section3d_nh_send_back': 0,
                'section3d_nh_completion_percent': 0.0,
                'section3d_nh_info': {
                    'total': counts['section3d_nh']['total'],
                    'draft_count': 0,
                    'submitted_count': 0,
                    'approved_count': 0,
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': True,
                    'is_completed': True,
                    'first_pending_id': False,
                    'first_document_id': False,
                },
                
                # Mutual Consent Policy (has village_id)
                'mutual_consent_policy_total': counts['mutual_consent_policy']['total'],
                'mutual_consent_policy_draft': counts['mutual_consent_policy']['draft'],
                'mutual_consent_policy_submitted': counts['mutual_consent_policy']['submitted'],
                'mutual_consent_policy_approved': counts['mutual_consent_policy']['approved'],
                'mutual_consent_policy_send_back': counts['mutual_consent_policy']['send_back'],
                'mutual_consent_policy_completion_percent': self._calculate_completion_percentage(
                    counts['mutual_consent_policy']['approved'], 0, counts['mutual_consent_policy']['total'], is_survey=False
                ),
                'mutual_consent_policy_info': self._get_section_info('bhu.mutual.consent.policy', domains['final_domain']),
                
                # Section 23 Award (has village_id)
                'section23_award_total': counts['section23_award']['total'],
                'section23_award_draft': counts['section23_award']['draft'],
                'section23_award_submitted': counts['section23_award']['submitted'],
                'section23_award_approved': counts['section23_award']['approved'],
                'section23_award_send_back': counts['section23_award']['send_back'],
                'section23_award_completion_percent': self._calculate_completion_percentage(
                    counts['section23_award']['approved'], 0, counts['section23_award']['total'], is_survey=False
                ),
                'section23_award_info': self._get_section_info('bhu.section23.award', domains['final_domain']),

            }
            
            return result
            
        except Exception as e:
            _logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
            # Return zeros on error
            return self._get_empty_stats()

    @api.model
    def _get_empty_stats(self):
        """Return empty stats structure for error cases"""
        is_collector = self.is_collector_user()
        empty_info = {
            'total': 0, 'submitted_count': 0, 'approved_count': 0, 'rejected_count': 0,
            'send_back_count': 0, 'all_approved': True, 'is_completed': True,
            'first_pending_id': False, 'first_document_id': False,
        }
        
        return {
            'is_collector': is_collector,
            'is_project_exempt': False,
            'user_type': 'other',
            'allowed_section_names': [],  # Empty list when no project selected
            'survey_total': 0, 'survey_draft': 0, 'survey_submitted': 0, 'survey_approved': 0, 'survey_rejected': 0,
            'survey_completion_percent': 0, 'survey_info': empty_info.copy(),
            'section4_total': 0, 'section4_draft': 0, 'section4_submitted': 0, 'section4_approved': 0, 'section4_send_back': 0,
            'section4_completion_percent': 0, 'section4_info': empty_info.copy(),
            'section11_total': 0, 'section11_draft': 0, 'section11_submitted': 0, 'section11_approved': 0, 'section11_send_back': 0,
            'section11_completion_percent': 0, 'section11_info': empty_info.copy(),
            'section15_total': 0, 'section15_draft': 0, 'section15_submitted': 0, 'section15_approved': 0, 'section15_send_back': 0,
            'section15_completion_percent': 0, 'section15_info': empty_info.copy(),
            'section19_total': 0, 'section19_draft': 0, 'section19_submitted': 0, 'section19_approved': 0, 'section19_send_back': 0,
            'section19_completion_percent': 0, 'section19_info': empty_info.copy(),
            'expert_total': 0, 'expert_draft': 0, 'expert_submitted': 0, 'expert_approved': 0, 'expert_send_back': 0,
            'expert_completion_percent': 0, 'expert_info': empty_info.copy(),
            'sia_total': 0, 'sia_draft': 0, 'sia_submitted': 0, 'sia_approved': 0, 'sia_send_back': 0,
            'sia_completion_percent': 0, 'sia_info': empty_info.copy(),
            'section8_total': 0, 'section8_draft': 0, 'section8_approved': 0, 'section8_rejected': 0,
            'section8_completion_percent': 0, 'section8_info': empty_info.copy(),
            'draft_award_total': 0, 'draft_award_draft': 0, 'draft_award_submitted': 0, 'draft_award_approved': 0, 'draft_award_send_back': 0,
            'draft_award_completion_percent': 0, 'draft_award_info': empty_info.copy(),
            # Railway Act Sections
            'section20a_railways_total': 0, 'section20a_railways_draft': 0, 'section20a_railways_submitted': 0,
            'section20a_railways_approved': 0, 'section20a_railways_send_back': 0, 'section20a_railways_completion_percent': 0,
            'section20a_railways_info': empty_info.copy(),
            'section20d_railways_total': 0, 'section20d_railways_draft': 0, 'section20d_railways_submitted': 0,
            'section20d_railways_approved': 0, 'section20d_railways_send_back': 0, 'section20d_railways_completion_percent': 0,
            'section20d_railways_info': empty_info.copy(),
            'section20e_railways_total': 0, 'section20e_railways_draft': 0, 'section20e_railways_submitted': 0,
            'section20e_railways_approved': 0, 'section20e_railways_send_back': 0, 'section20e_railways_completion_percent': 0,
            'section20e_railways_info': empty_info.copy(),
            # National Highway Act Sections
            'section3a_nh_total': 0, 'section3a_nh_draft': 0, 'section3a_nh_submitted': 0,
            'section3a_nh_approved': 0, 'section3a_nh_send_back': 0, 'section3a_nh_completion_percent': 0,
            'section3a_nh_info': empty_info.copy(),
            'section3c_nh_total': 0, 'section3c_nh_draft': 0, 'section3c_nh_submitted': 0,
            'section3c_nh_approved': 0, 'section3c_nh_send_back': 0, 'section3c_nh_completion_percent': 0,
            'section3c_nh_info': empty_info.copy(),
            'section3d_nh_total': 0, 'section3d_nh_draft': 0, 'section3d_nh_submitted': 0,
            'section3d_nh_approved': 0, 'section3d_nh_send_back': 0, 'section3d_nh_completion_percent': 0,
            'section3d_nh_info': empty_info.copy(),
            # Mutual Consent Policy
            'mutual_consent_policy_total': 0, 'mutual_consent_policy_draft': 0, 'mutual_consent_policy_submitted': 0,
            'mutual_consent_policy_approved': 0, 'mutual_consent_policy_send_back': 0, 'mutual_consent_policy_completion_percent': 0,
            'mutual_consent_policy_info': empty_info.copy(),
            # Section 23 Award
            'section23_award_total': 0, 'section23_award_draft': 0, 'section23_award_submitted': 0,
            'section23_award_approved': 0, 'section23_award_send_back': 0, 'section23_award_completion_percent': 0,
            'section23_award_info': empty_info.copy(),
        }

    # ========== Generic Data Methods ==========
    
    @api.model
    def get_user_projects(self, department_id=None):
        """Get projects accessible to current user, optionally filtered by department
        
        This method automatically determines user access based on their role:
        - Admin/Collector: See all projects
        - SDM/Tehsildar: See only assigned projects
        - Department User: See projects in their department
        - Others: See only assigned projects
        
        Args:
            department_id: Optional department ID to filter by (can be int, string, or None)
            
        Returns:
            list: List of project dictionaries with 'id' and 'name'
        """
        # Convert department_id to int if provided
        dept_id = None
        if department_id:
            try:
                dept_id = int(department_id)
            except (ValueError, TypeError):
                _logger.warning(f"Invalid department_id provided: {department_id}, ignoring filter")
                dept_id = None
        
        user_access = self._get_user_project_access()
        _logger.info(f"get_user_projects called - user: {self.env.user.name} (ID: {self.env.user.id}), "
                    f"can_see_all: {user_access['can_see_all']}, department_id: {dept_id}")
        
        domain = []
        
        if user_access['can_see_all']:
            # Admin/Collector/District Admin: can see all, optionally filter by department
            if dept_id:
                domain = [('department_id', '=', dept_id)]
            projects = self.env['bhu.project'].search(domain)
            _logger.info(f"Found {len(projects)} projects (can_see_all=True, dept_filter={dept_id})")
        else:
            # User has project restrictions
            project_ids = user_access['project_ids'] or []
            if project_ids:
                domain = [('id', 'in', project_ids)]
                if dept_id:
                    domain = ['&', ('department_id', '=', dept_id)] + domain
                projects = self.env['bhu.project'].search(domain)
                _logger.info(f"Found {len(projects)} projects (restricted access, dept_filter={dept_id})")
            else:
                _logger.warning(f"No project_ids found for user {self.env.user.name} (ID: {self.env.user.id})")
                return []
        
        result = projects.read(["id", "name"])
        _logger.info(f"Returning {len(result)} projects: {[p['name'] for p in result]}")
        return result
    
    @api.model
    def get_villages_by_project(self, project_id):
        """Get villages for a specific project
        
        Args:
            project_id: Project ID to get villages for
            
        Returns:
            list: List of village dictionaries with 'id' and 'name'
        """
        project = self.env["bhu.project"].browse(project_id)
        if not project.exists():
            return []
        villages = project.village_ids
        return villages.read(["id", "name"])

    # ========== Legacy Methods (for backward compatibility) ==========
    # These methods redirect to generic methods above
    
    @api.model
    def get_sdm_dashboard_stats(self, department_id=None, project_id=None, village_id=None):
        """Legacy method name - redirects to get_dashboard_stats for backward compatibility"""
        return self.get_dashboard_stats(department_id, project_id, village_id)
    
    @api.model
    def get_all_projects_sdm(self):
        """Legacy method - redirects to get_user_projects()"""
        return self.get_user_projects()
    
    @api.model
    def get_all_projects_sdm_filtered(self, department_id=None):
        """Legacy method - redirects to get_user_projects(department_id)"""
        return self.get_user_projects(department_id)
    
    @api.model
    def get_villages_by_project_sdm(self, project_id):
        """Legacy method - redirects to get_villages_by_project(project_id)"""
        return self.get_villages_by_project(project_id)

