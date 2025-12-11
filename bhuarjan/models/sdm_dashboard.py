from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class BhuDashboard(models.Model):
    _name = "bhu.dashboard"
    _description = 'Bhuarjan Dashboard'

    @api.model
    def get_all_projects(self):
        """Get projects for current user"""
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
    def get_all_departments(self):
        """Get departments - filtered by user's assigned projects for SDM/Tehsildar, all for admin/collector"""
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
    def get_all_projects_sdm(self, department_id=None):
        """Get projects for current user (SDM or Tehsildar), optionally filtered by department"""
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
        """Get villages for a specific project"""
        project = self.env["bhu.project"].browse(project_id)
        if not project.exists():
            return []
        villages = project.village_ids
        return villages.read(["id", "name"])

    @api.model
    def is_collector_user(self):
        """Check if current user is Collector"""
        return self.env.user.has_group('bhuarjan.group_bhuarjan_collector') or \
               self.env.user.has_group('bhuarjan.group_bhuarjan_additional_collector') or \
               self.env.user.has_group('bhuarjan.group_bhuarjan_admin') or \
               self.env.user.has_group('base.group_system')

    @api.model
    def get_sdm_dashboard_stats(self, department_id=None, project_id=None, village_id=None):
        """Get dashboard statistics for SDM/Collector filtered by assigned projects"""
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
            
            # Get counts first
            survey_total = self.env['bhu.survey'].search_count(final_domain)
            survey_approved = self.env['bhu.survey'].search_count(final_domain + [('state', '=', 'approved')])
            survey_rejected = self.env['bhu.survey'].search_count(final_domain + [('state', '=', 'rejected')])
            
            section4_total = self.env['bhu.section4.notification'].search_count(final_domain)
            section4_approved = self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'approved')])
            
            section11_total = self.env['bhu.section11.preliminary.report'].search_count(final_domain)
            section11_approved = self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'approved')])
            
            section15_total = self.env['bhu.section15.objection'].search_count(final_domain)
            section15_approved = self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'approved')])
            
            section19_total = self.env['bhu.section19.notification'].search_count(final_domain)
            section19_approved = self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'approved')])
            
            expert_total = self.env['bhu.expert.committee.report'].search_count(final_domain)
            expert_approved = self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'approved')])
            
            sia_total = self.env['bhu.sia.team'].search_count(final_domain)
            sia_approved = self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'approved')])
            
            draft_award_total = self.env['bhu.draft.award'].search_count(final_domain)
            draft_award_approved = self.env['bhu.draft.award'].search_count(final_domain + [('state', '=', 'signed')])
            
            return {
                'is_collector': is_collector,
                # Surveys - State wise
                'survey_total': survey_total,
                'survey_draft': self.env['bhu.survey'].search_count(final_domain + [('state', '=', 'draft')]),
                'survey_submitted': self.env['bhu.survey'].search_count(final_domain + [('state', '=', 'submitted')]),
                'survey_approved': survey_approved,
                'survey_rejected': survey_rejected,
                'survey_completion_percent': calculate_completion_percentage(survey_approved, survey_rejected, survey_total, is_survey=True),
                'survey_info': get_section_info('bhu.survey', final_domain, 'state', is_survey=True),
                
                # Section 4 Notifications - State wise (village-based completion)
                'section4_total': section4_total,
                'section4_draft': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'draft')]),
                'section4_submitted': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section4_approved': section4_approved,
                'section4_send_back': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section4_completion_percent': calculate_village_based_completion('bhu.section4.notification', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section4_info': get_section_info('bhu.section4.notification', final_domain),
                
                # Section 11 Reports - State wise (village-based completion)
                'section11_total': section11_total,
                'section11_draft': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'draft')]),
                'section11_submitted': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section11_approved': section11_approved,
                'section11_send_back': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section11_completion_percent': calculate_village_based_completion('bhu.section11.preliminary.report', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section11_info': get_section_info('bhu.section11.preliminary.report', final_domain),
                
                # Section 15 Objections - State wise
                'section15_total': section15_total,
                'section15_draft': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'draft')]),
                'section15_submitted': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section15_approved': section15_approved,
                'section15_send_back': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section15_completion_percent': calculate_completion_percentage(section15_approved, 0, section15_total, is_survey=False),
                'section15_info': get_section_info('bhu.section15.objection', final_domain),
                
                # Section 19 Notifications - State wise (village-based completion)
                'section19_total': section19_total,
                'section19_draft': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'draft')]),
                'section19_submitted': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section19_approved': section19_approved,
                'section19_send_back': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section19_completion_percent': calculate_village_based_completion('bhu.section19.notification', project_ids_from_domain) if project_ids_from_domain else 0.0,
                'section19_info': get_section_info('bhu.section19.notification', final_domain),
                
                # Expert Committee Reports - State wise
                'expert_total': expert_total,
                'expert_draft': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'draft')]),
                'expert_submitted': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'submitted')]),
                'expert_approved': expert_approved,
                'expert_send_back': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'send_back')]),
                'expert_completion_percent': calculate_completion_percentage(expert_approved, 0, expert_total, is_survey=False),
                'expert_info': get_section_info('bhu.expert.committee.report', final_domain),
                
                # SIA Teams - State wise
                'sia_total': sia_total,
                'sia_draft': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'draft')]),
                'sia_submitted': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'submitted')]),
                'sia_approved': sia_approved,
                'sia_send_back': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'send_back')]),
                'sia_completion_percent': calculate_completion_percentage(sia_approved, 0, sia_total, is_survey=False),
                'sia_info': get_section_info('bhu.sia.team', final_domain),
                
                # Draft Award - State wise (uses 'signed' state instead of 'approved')
                'draft_award_total': draft_award_total,
                'draft_award_draft': self.env['bhu.draft.award'].search_count(final_domain + [('state', '=', 'draft')]),
                'draft_award_generated': self.env['bhu.draft.award'].search_count(final_domain + [('state', '=', 'generated')]),
                'draft_award_approved': draft_award_approved,  # 'signed' state
                'draft_award_completion_percent': calculate_completion_percentage(draft_award_approved, 0, draft_award_total, is_survey=False),
                'draft_award_info': {
                    'total': draft_award_total,
                    'submitted_count': self.env['bhu.draft.award'].search_count(final_domain + [('state', '=', 'generated')]),
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