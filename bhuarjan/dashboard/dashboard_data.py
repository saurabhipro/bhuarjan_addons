# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DashboardData(models.AbstractModel):
    """Dashboard data fetching methods"""
    _name = 'bhuarjan.dashboard.data'
    _description = 'Dashboard Data Methods'

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
        """Get projects accessible to current user, optionally filtered by department
        
        NOTE: This method is now handled by dashboard_stats.get_user_projects()
        which uses unified access logic. This method is kept for backward compatibility.
        
        Args:
            department_id: Optional department ID to filter by
            
        Returns:
            list: List of project dictionaries with 'id' and 'name'
        """
        # The unified method get_user_projects() from dashboard_stats will be used
        # when called on bhuarjan.dashboard model (which inherits from both)
        # This is a fallback for direct calls to dashboard_data model
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
        """Get villages for a specific project
        
        NOTE: This method is now handled by dashboard_stats.get_villages_by_project()
        which is identical. This method is kept for backward compatibility.
        
        Args:
            project_id: Project ID to get villages for
            
        Returns:
            list: List of village dictionaries with 'id' and 'name'
        """
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
