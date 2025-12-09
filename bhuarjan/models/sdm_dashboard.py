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
        """Get all departments"""
        departments = self.env['bhu.department'].search([])
        return departments.read(["id", "name"])

    @api.model
    def get_all_projects_sdm(self, department_id=None):
        """Get projects for SDM, optionally filtered by department"""
        if self.env.user.has_group('bhuarjan.group_bhuarjan_sdm'):
            domain = [('sdm_ids', 'in', [self.env.user.id])]
            if department_id:
                domain.append(('department_id', '=', department_id))
            projects = self.env['bhu.project'].search(domain)
        else:
            projects = self.env['bhu.project'].search([])
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
        """Get dashboard statistics for SDM filtered by assigned projects"""
        try:
            # Get SDM's assigned projects
            if self.env.user.has_group('bhuarjan.group_bhuarjan_sdm'):
                assigned_projects = self.env['bhu.project'].search([
                    ('sdm_ids', 'in', [self.env.user.id])
                ])
                project_ids = assigned_projects.ids
                
                # Build domain filters
                project_domain = []
                village_domain = []
                
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
                    project_domain = [('project_id', 'in', project_ids)] if project_ids else [('project_id', '=', False)]
                
                # Filter by village if provided
                if village_id:
                    village_domain = [('village_id', '=', village_id)]
                
                # Combine domains
                final_domain = project_domain + village_domain if (project_domain or village_domain) else project_domain
            else:
                # Not SDM, return zeros or all (depending on requirement)
                final_domain = []
                if project_id:
                    final_domain.append(('project_id', '=', project_id))
                if village_id:
                    final_domain.append(('village_id', '=', village_id))

            # Helper function to get first pending document and check if all approved
            def get_section_info(model_name, domain):
                records = self.env[model_name].search(domain, order='create_date asc')
                total = len(records)
                submitted = records.filtered(lambda r: r.state == 'submitted')
                approved = records.filtered(lambda r: r.state == 'approved')
                all_approved = total > 0 and len(approved) == total
                first_pending = submitted[0] if submitted else False
                first_document = records[0] if records else False
                return {
                    'total': total,
                    'submitted_count': len(submitted),
                    'approved_count': len(approved),
                    'all_approved': all_approved,
                    'first_pending_id': first_pending.id if first_pending else False,
                    'first_document_id': first_document.id if first_document else False,
                }

            is_collector = self.is_collector_user()
            
            return {
                'is_collector': is_collector,
                # Section 4 Notifications - State wise
                'section4_total': self.env['bhu.section4.notification'].search_count(final_domain),
                'section4_draft': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'draft')]),
                'section4_submitted': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section4_approved': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'approved')]),
                'section4_send_back': self.env['bhu.section4.notification'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section4_info': get_section_info('bhu.section4.notification', final_domain),
                
                # Section 11 Reports - State wise
                'section11_total': self.env['bhu.section11.preliminary.report'].search_count(final_domain),
                'section11_draft': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'draft')]),
                'section11_submitted': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section11_approved': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'approved')]),
                'section11_send_back': self.env['bhu.section11.preliminary.report'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section11_info': get_section_info('bhu.section11.preliminary.report', final_domain),
                
                # Section 15 Objections - State wise
                'section15_total': self.env['bhu.section15.objection'].search_count(final_domain),
                'section15_draft': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'draft')]),
                'section15_submitted': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section15_approved': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'approved')]),
                'section15_send_back': self.env['bhu.section15.objection'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section15_info': get_section_info('bhu.section15.objection', final_domain),
                
                # Section 19 Notifications - State wise
                'section19_total': self.env['bhu.section19.notification'].search_count(final_domain),
                'section19_draft': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'draft')]),
                'section19_submitted': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'submitted')]),
                'section19_approved': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'approved')]),
                'section19_send_back': self.env['bhu.section19.notification'].search_count(final_domain + [('state', '=', 'send_back')]),
                'section19_info': get_section_info('bhu.section19.notification', final_domain),
                
                # Expert Committee Reports - State wise
                'expert_total': self.env['bhu.expert.committee.report'].search_count(final_domain),
                'expert_draft': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'draft')]),
                'expert_submitted': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'submitted')]),
                'expert_approved': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'approved')]),
                'expert_send_back': self.env['bhu.expert.committee.report'].search_count(final_domain + [('state', '=', 'send_back')]),
                'expert_info': get_section_info('bhu.expert.committee.report', final_domain),
                
                # SIA Teams - State wise
                'sia_total': self.env['bhu.sia.team'].search_count(final_domain),
                'sia_draft': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'draft')]),
                'sia_submitted': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'submitted')]),
                'sia_approved': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'approved')]),
                'sia_send_back': self.env['bhu.sia.team'].search_count(final_domain + [('state', '=', 'send_back')]),
                'sia_info': get_section_info('bhu.sia.team', final_domain),
            }
        except Exception as e:
            _logger.error(f"Error getting SDM dashboard stats: {e}", exc_info=True)
            # Return zeros on error
            return {
                'is_collector': False,
                'section4_total': 0, 'section4_draft': 0, 'section4_submitted': 0, 'section4_approved': 0, 'section4_send_back': 0,
                'section4_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
                'section11_total': 0, 'section11_draft': 0, 'section11_submitted': 0, 'section11_approved': 0, 'section11_send_back': 0,
                'section11_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
                'section15_total': 0, 'section15_draft': 0, 'section15_submitted': 0, 'section15_approved': 0, 'section15_send_back': 0,
                'section15_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
                'section19_total': 0, 'section19_draft': 0, 'section19_submitted': 0, 'section19_approved': 0, 'section19_send_back': 0,
                'section19_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
                'expert_total': 0, 'expert_draft': 0, 'expert_submitted': 0, 'expert_approved': 0, 'expert_send_back': 0,
                'expert_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
                'sia_total': 0, 'sia_draft': 0, 'sia_submitted': 0, 'sia_approved': 0, 'sia_send_back': 0,
                'sia_info': {'total': 0, 'submitted_count': 0, 'approved_count': 0, 'all_approved': True, 'first_pending_id': False, 'first_document_id': False},
            }