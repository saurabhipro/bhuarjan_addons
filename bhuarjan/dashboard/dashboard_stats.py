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
        ],
        'sdm_groups': [
            'bhuarjan.group_bhuarjan_sdm',             # SDM users
        ],
        'tehsildar_groups': [
            # Add tehsildar-specific groups here if they exist
            # Example: 'bhuarjan.group_bhuarjan_tehsildar',
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
    ]

    # Models that don't have village_id field (only project filtering)
    MODELS_WITHOUT_VILLAGE = [
        'bhu.expert.committee.report',
        'bhu.sia.team',
        'bhu.draft.award',
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
            return {
                'can_see_all': True,
                'project_ids': None,
                'user_type': 'admin' if user.has_group('bhuarjan.group_bhuarjan_admin') or user.has_group('base.group_system') else 'collector',
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
            if department_id and not project_id:
                dept_projects = self.env['bhu.project'].search([('department_id', '=', department_id)])
                project_domain = [('project_id', 'in', dept_projects.ids)] if dept_projects else [('project_id', '=', False)]
            elif project_id:
                project_domain = [('project_id', '=', project_id)]
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
        
        # Combine domains
        if project_domain:
            final_domain = project_domain + village_domain if village_domain else project_domain
        elif village_domain:
            final_domain = village_domain
        else:
            final_domain = []
        
        # Domain for models without village_id (only project filter)
        domain_without_village = project_domain if project_domain else []
        
        # Extract project IDs for completion calculations
        project_ids_from_domain = self._extract_project_ids(project_id, project_domain, department_id, user_access)
        
        return {
            'project_domain': project_domain,
            'village_domain': village_domain,
            'final_domain': final_domain,
            'domain_without_village': domain_without_village,
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
            float: Completion percentage
        """
        if total == 0:
            return 0.0
        if is_survey:
            return round(((approved + rejected) / total) * 100, 1)
        else:
            return round((approved / total) * 100, 1)

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
        
        # Get counts using generic methods
        counts = {
            'survey': self._get_survey_counts(domain_with_village),
            'section4': self._get_section_counts('bhu.section4.notification', domain_with_village),
            'section11': self._get_section_counts('bhu.section11.preliminary.report', domain_with_village),
            'section15': self._get_section_counts('bhu.section15.objection', domain_with_village),
            'section19': self._get_section_counts('bhu.section19.notification', domain_with_village),
            'expert': self._get_section_counts('bhu.expert.committee.report', domain_without_village),
            'sia': self._get_section_counts('bhu.sia.team', domain_without_village),
        }
        
        # Draft Award uses 'signed' state instead of 'approved'
        counts['draft_award'] = {
            'total': self._get_model_count_by_status('bhu.draft.award', domain_without_village, None),
            'approved': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'signed'),
            'draft': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'draft'),
            'generated': self._get_model_count_by_status('bhu.draft.award', domain_without_village, 'generated'),
        }
        
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
    def get_dashboard_stats(self, department_id=None, project_id=None, village_id=None):
        """Get unified dashboard statistics for all dashboard types
        
        This method works for:
        - SDM Dashboard
        - Collector Dashboard
        - Admin Dashboard
        - Department Dashboard
        - District Admin Dashboard
        - Any other dashboard type
        
        Args:
            department_id: Optional department ID to filter by
            project_id: Optional project ID to filter by
            village_id: Optional village ID to filter by
            
        Returns:
            dict: Complete dashboard statistics
        """
        try:
            # Build filter domains based on user access
            domains = self._build_filter_domains(department_id, project_id, village_id)
            
            # Get user info
            user_access = self._get_user_project_access()
            is_collector = self.is_collector_user()
            
            # Get project exemption status
            is_project_exempt = False
            if project_id:
                project = self.env['bhu.project'].browse(project_id)
                if project.exists():
                    is_project_exempt = project.is_sia_exempt or False
            
            # Get total villages for completion calculations
            total_villages = self._get_total_villages(domains['project_ids_from_domain'])
            
            # Get all section counts
            counts = self._get_all_section_counts(domains)
            
            # Build response with all statistics
            result = {
                'is_collector': is_collector,
                'is_project_exempt': is_project_exempt,
                'user_type': user_access['user_type'],
                
                # Surveys
                'survey_total': counts['survey']['total'],
                'survey_draft': counts['survey']['draft'],
                'survey_submitted': counts['survey']['submitted'],
                'survey_approved': counts['survey']['approved'],
                'survey_rejected': counts['survey']['rejected'],
                'survey_completion_percent': counts['survey']['completion_percent'],
                'survey_info': self._get_section_info('bhu.survey', domains['final_domain'], 'state', is_survey=True),
                
                # Section 4
                'section4_total': counts['section4']['total'],
                'section4_draft': counts['section4']['draft'],
                'section4_submitted': counts['section4']['submitted'],
                'section4_approved': counts['section4']['approved'],
                'section4_send_back': counts['section4']['send_back'],
                'section4_completion_percent': self._calculate_village_based_completion(
                    'bhu.section4.notification', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section4_info': self._get_section_info('bhu.section4.notification', domains['final_domain']),
                
                # Section 11
                'section11_total': counts['section11']['total'],
                'section11_draft': counts['section11']['draft'],
                'section11_submitted': counts['section11']['submitted'],
                'section11_approved': counts['section11']['approved'],
                'section11_send_back': counts['section11']['send_back'],
                'section11_completion_percent': self._calculate_village_based_completion(
                    'bhu.section11.preliminary.report', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section11_info': self._get_section_info('bhu.section11.preliminary.report', domains['final_domain']),
                
                # Section 15
                'section15_total': counts['section15']['total'],
                'section15_draft': counts['section15']['draft'],
                'section15_submitted': counts['section15']['submitted'],
                'section15_approved': counts['section15']['approved'],
                'section15_send_back': counts['section15']['send_back'],
                'section15_completion_percent': self._calculate_completion_percentage(
                    counts['section15']['approved'], 0, counts['section15']['total'], is_survey=False
                ),
                'section15_info': self._get_section_info('bhu.section15.objection', domains['final_domain']),
                
                # Section 19
                'section19_total': counts['section19']['total'],
                'section19_draft': counts['section19']['draft'],
                'section19_submitted': counts['section19']['submitted'],
                'section19_approved': counts['section19']['approved'],
                'section19_send_back': counts['section19']['send_back'],
                'section19_completion_percent': self._calculate_village_based_completion(
                    'bhu.section19.notification', domains['project_ids_from_domain'], total_villages
                ) if domains['project_ids_from_domain'] else 0.0,
                'section19_info': self._get_section_info('bhu.section19.notification', domains['final_domain']),
                
                # Expert Committee
                'expert_total': counts['expert']['total'],
                'expert_draft': counts['expert']['draft'],
                'expert_submitted': counts['expert']['submitted'],
                'expert_approved': counts['expert']['approved'],
                'expert_send_back': counts['expert']['send_back'],
                'expert_completion_percent': self._calculate_completion_percentage(
                    counts['expert']['approved'], 0, counts['expert']['total'], is_survey=False
                ),
                'expert_info': self._get_section_info('bhu.expert.committee.report', domains['final_domain']),
                
                # SIA Teams
                'sia_total': counts['sia']['total'],
                'sia_draft': counts['sia']['draft'],
                'sia_submitted': counts['sia']['submitted'],
                'sia_approved': counts['sia']['approved'],
                'sia_send_back': counts['sia']['send_back'],
                'sia_completion_percent': self._calculate_completion_percentage(
                    counts['sia']['approved'], 0, counts['sia']['total'], is_survey=False
                ),
                'sia_info': self._get_section_info('bhu.sia.team', domains['final_domain']),
                
                # Draft Award
                'draft_award_total': counts['draft_award']['total'],
                'draft_award_draft': counts['draft_award']['draft'],
                'draft_award_generated': counts['draft_award']['generated'],
                'draft_award_approved': counts['draft_award']['approved'],
                'draft_award_completion_percent': self._calculate_completion_percentage(
                    counts['draft_award']['approved'], 0, counts['draft_award']['total'], is_survey=False
                ),
                'draft_award_info': {
                    'total': counts['draft_award']['total'],
                    'submitted_count': counts['draft_award']['generated'],
                    'approved_count': counts['draft_award']['approved'],
                    'rejected_count': 0,
                    'send_back_count': 0,
                    'all_approved': counts['draft_award']['total'] > 0 and counts['draft_award']['approved'] == counts['draft_award']['total'],
                    'is_completed': counts['draft_award']['total'] > 0 and counts['draft_award']['approved'] == counts['draft_award']['total'],
                    'first_pending_id': False,
                    'first_document_id': False,
                },
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
            'draft_award_total': 0, 'draft_award_draft': 0, 'draft_award_generated': 0, 'draft_award_approved': 0,
            'draft_award_completion_percent': 0, 'draft_award_info': empty_info.copy(),
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
            department_id: Optional department ID to filter by
            
        Returns:
            list: List of project dictionaries with 'id' and 'name'
        """
        user_access = self._get_user_project_access()
        domain = []
        
        if user_access['can_see_all']:
            # Admin/Collector: can see all, optionally filter by department
            if department_id:
                domain = [('department_id', '=', department_id)]
            projects = self.env['bhu.project'].search(domain)
        else:
            # User has project restrictions
            project_ids = user_access['project_ids'] or []
            if project_ids:
                domain = [('id', 'in', project_ids)]
                if department_id:
                    domain = ['&', ('department_id', '=', department_id)] + domain
                projects = self.env['bhu.project'].search(domain)
            else:
                return []
        
        return projects.read(["id", "name"])
    
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

