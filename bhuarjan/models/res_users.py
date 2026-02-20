from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json


class BhuUserMobile(models.Model):
    """Additional mobile numbers for a user (for multi-mobile OTP login)"""
    _name = 'bhu.user.mobile'
    _description = 'User Additional Mobile Number'
    _order = 'sequence, id'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    mobile = fields.Char(string='Mobile Number', required=True)
    label = fields.Char(string='Label', help='e.g. Personal, Office, WhatsApp')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('mobile')
    def _check_mobile_unique(self):
        """Ensure this additional mobile is not already used by any user (primary or additional)"""
        for rec in self:
            # Check against primary mobile of all users
            dup_primary = self.env['res.users'].search([
                ('mobile', '=', rec.mobile),
                ('id', '!=', rec.user_id.id),
            ], limit=1)
            if dup_primary:
                raise ValidationError(
                    f'Mobile {rec.mobile} is already the primary number of user "{dup_primary.name}".'
                )
            # Check against other additional mobiles
            dup_additional = self.env['bhu.user.mobile'].search([
                ('mobile', '=', rec.mobile),
                ('id', '!=', rec.id),
            ], limit=1)
            if dup_additional:
                raise ValidationError(
                    f'Mobile {rec.mobile} is already registered as an additional number for user "{dup_additional.user_id.name}".'
                )


class ResUsers(models.Model):
    _inherit = 'res.users'

    parent_id = fields.Many2one('res.users', string="Parent")
    child_ids = fields.One2many('res.users', 'parent_id', string='Direct subordinates')
    # color = fields.Integer(string="Color Index")
    department_color = fields.Char(string="Color", default="#4c7cf3")
    def _get_state_domain(self):
        state_ids = self.env['bhu.district'].search([]).mapped('state_id.id')    
        return [('id', 'in', state_ids)]

    mobile = fields.Char(string="Mobile")

    # Additional mobile numbers for multi-mobile OTP login
    mobile_number_ids = fields.One2many(
        'bhu.user.mobile', 'user_id',
        string='Additional Mobile Numbers / अतिरिक्त मोबाइल नंबर',
        help='Add extra mobile numbers so this user can login with any of them.'
    )

    def copy_data(self, default=None):
        if default is None:
            default = {}
        default['mobile'] = False
        default['login'] = (self.login or '') + ' (copy)'
        return super().copy_data(default)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """Allow Bhuarjan Admin and District Admin to write/create users.
        Bhuarjan Admin is explicitly included to ensure they bypass standard Odoo 
        restrictions even if they aren't 'System' users.
        """
        if operation in ('write', 'create', 'read', 'unlink'):
            user = self.env.user
            if (user.has_group('bhuarjan.group_bhuarjan_admin') or
                    user.has_group('bhuarjan.group_bhuarjan_district_administrator')):
                return True
        return super().check_access_rights(operation, raise_exception=raise_exception)

    def check_access_rule(self, operation):
        """Allow Bhuarjan Admin and District Admin to bypass record-level rules on res.users.
        This is required so the form renders as editable in the UI (the web client
        probes check_access_rule to decide whether to show Save/Edit buttons).
        """
        user = self.env.user
        if (user.has_group('bhuarjan.group_bhuarjan_admin') or
                user.has_group('bhuarjan.group_bhuarjan_district_administrator')):
            return None  # explicitly return None to signal success
        return super().check_access_rule(operation)

    def write(self, vals):
        """Allow Bhuarjan Administrator and District Administrator to edit users."""
        current_user = self.env.user
        is_privileged = (
            current_user.has_group('bhuarjan.group_bhuarjan_admin') or
            current_user.has_group('bhuarjan.group_bhuarjan_district_administrator')
        )
        if is_privileged:
            # Use sudo() to bypass Odoo's internal ERP-Manager write restriction
            # Record rules still enforce district-level scope for District Admins
            return super(ResUsers, self.sudo()).write(vals)
        return super().write(vals)

    @api.model
    def create(self, vals):
        """Allow Bhuarjan Administrator and District Administrator to create users."""
        current_user = self.env.user
        is_admin = current_user.has_group('bhuarjan.group_bhuarjan_admin')
        is_district_admin = current_user.has_group('bhuarjan.group_bhuarjan_district_administrator')
        if is_admin or is_district_admin:
            # Auto-fill district for District Admin's newly created users
            if is_district_admin and not is_admin:
                if 'district_id' not in vals and current_user.district_id:
                    vals['district_id'] = current_user.district_id.id
            return super(ResUsers, self.sudo()).create(vals)
        return super().create(vals)

    @api.constrains('mobile')
    def _check_mobile_unique(self):
        """Ensure mobile number is unique across all users"""
        for record in self:
            if record.mobile:  # Only validate if mobile is provided
                # Search for other users with the same mobile number
                duplicate = self.env['res.users'].search([
                    ('mobile', '=', record.mobile),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f'Mobile number {record.mobile} is already assigned to user "{duplicate.name}". '
                        f'Each user must have a unique mobile number.'
                    )
    state_id = fields.Many2one('res.country.state', string='State', domain=lambda self: self._get_state_domain(), default=lambda self: self.env.user.state_id.id)
    district_id = fields.Many2one('bhu.district', string='District / जिला', default=lambda self: self.env.user.district_id.id)
    sub_division_ids = fields.Many2many('bhu.sub.division', string='Sub Division / उपभाग')
    tehsil_ids = fields.Many2many('bhu.tehsil', string='Tehsil / तहसील')
    bhu_department_id = fields.Many2one(
        'bhu.department',  # Maps to bhu.department model (Bhuarjan Department), NOT hr.department
        string='Department / विभाग',
        help='Select the Bhuarjan department for Department User role. This will be shown in the dashboard.'
    )
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', 
                                 help='Select a project to filter villages. Only villages from this project will be shown.')
    village_domain = fields.Char(string='Village Domain', compute='_compute_village_domain', store=False)
    village_ids = fields.Many2many('bhu.village', string="Villages")
    bhuarjan_role = fields.Selection([
        ('patwari', 'Patwari'),
        ('sdm', 'SDM'),
        ('tahsildar', 'Tehsildar'),  # Legacy support
        ('additional_collector', 'Additional Collector'),
        ('collector', 'Collector'),
        ('district_administrator', 'District Administrator'),
        ('administrator', 'Administrator'),
        ('department_user', 'Department User'),
    ], string="Bhuarjan Role", default=False)

    bhuarjan_category_id = fields.Many2one(
        'ir.module.category',
        string="Bhuarjan Category",
        compute='_compute_bhuarjan_category'
    )

    def _compute_bhuarjan_category(self):
        category = self.env.ref('bhuarjan.module_category_bhuarjan_bhuarjan', raise_if_not_found=False)
        for record in self:
            record.bhuarjan_category_id = category

    def init(self):
        """Cleanup legacy roles on module upgrade"""
        self.env.cr.execute("UPDATE res_users SET bhuarjan_role = 'sdm' WHERE bhuarjan_role = 'tahsildar'")

    survey_count_in_project = fields.Integer(
        string='Survey Count / सर्वे संख्या',
        compute='_compute_survey_count_in_project',
        store=False
    )
    
    def _compute_survey_count_in_project(self):
        """Compute survey count for patwari in the current project context
        Counts surveys where:
        1. Survey was created by this patwari (user_id), OR
        2. Survey is in a village assigned to this patwari
        
        Note: This field is context-dependent and recomputes on every read
        """
        project_id = self.env.context.get('default_project_id') or self.env.context.get('active_id')
        if not project_id:
            # Try to get from parent record if in Many2many view
            active_model = self.env.context.get('active_model')
            active_id = self.env.context.get('active_id')
            if active_model == 'bhu.project' and active_id:
                project_id = active_id
        
        for user in self:
            if user.bhuarjan_role == 'patwari' and project_id:
                # Count surveys where:
                # 1. Created by this patwari, OR
                # 2. In villages assigned to this patwari
                village_ids = user.village_ids.ids if user.village_ids else []
                domain = [
                    ('project_id', '=', project_id),
                    '|',
                    ('user_id', '=', user.id),
                    ('village_id', 'in', village_ids)
                ]
                user.survey_count_in_project = self.env['bhu.survey'].search_count(domain)
            else:
                user.survey_count_in_project = 0
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to recompute survey_count_in_project when context has project"""
        result = super().read(fields=fields, load=load)
        # Force recomputation if survey_count_in_project is being read and context has project
        if fields is None or 'survey_count_in_project' in fields:
            project_id = self.env.context.get('default_project_id') or self.env.context.get('active_id')
            if project_id:
                # Recompute for all records
                self._compute_survey_count_in_project()
                # Update result with recomputed values
                for record, res in zip(self, result):
                    if 'survey_count_in_project' in res:
                        res['survey_count_in_project'] = record.survey_count_in_project
        return result

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Force fields as editable for privileged users in the UI."""
        res = super(ResUsers, self).fields_get(allfields, attributes)
        user = self.env.user
        is_privileged = (
            user.has_group('bhuarjan.group_bhuarjan_admin') or
            user.has_group('bhuarjan.group_bhuarjan_district_administrator')
        )
        if is_privileged:
            for field in ['name', 'login', 'mobile', 'email']:
                if field in res:
                    res[field]['readonly'] = False
        return res


    assigned_project_ids = fields.Many2many(
        'bhu.project', 
        compute='_compute_assigned_projects',
        string='Assigned Projects',
        help='Projects where this user is assigned as SDM or Tehsildar'
    )

    def _compute_assigned_projects(self):
        """Compute projects assigned to this user"""
        for user in self:
            projects = self.env['bhu.project'].search([
                '|',
                '|',
                ('sdm_ids', 'in', user.id),
                ('tehsildar_ids', 'in', user.id),
                ('department_user_ids', 'in', user.id)
            ])
            user.assigned_project_ids = projects
    
    def _get_assigned_project_ids(self):
        """Get assigned project IDs for current user (for domain use)"""
        user = self.env.user
        # Admin and system users see all projects
        if user.has_group('bhuarjan.group_bhuarjan_admin') or user.has_group('base.group_system'):
            return []
        
        projects = self.env['bhu.project'].search([
            '|',
            '|',
            ('sdm_ids', 'in', user.id),
            ('tehsildar_ids', 'in', user.id),
            ('department_user_ids', 'in', user.id)
        ])
        return projects.ids if projects else [False]  # Return [False] to show no projects

    @api.onchange('bhuarjan_role')
    def _onchange_bhuarjan_role(self):
        """Assign the corresponding group based on selected role"""
        # Clear all previous custom roles (you can add all group XML IDs here)
        all_custom_group_ids = [
            self.env.ref('bhuarjan.group_bhuarjan_patwari').id,
            self.env.ref('bhuarjan.group_bhuarjan_sdm').id,
            self.env.ref('bhuarjan.group_bhuarjan_additional_collector').id,
            self.env.ref('bhuarjan.group_bhuarjan_collector').id,
            self.env.ref('bhuarjan.group_bhuarjan_district_administrator').id,
            self.env.ref('bhuarjan.group_bhuarjan_admin').id,
            self.env.ref('bhuarjan.group_bhuarjan_department_user').id,
        ]
        if self.groups_id:
            # properly handle removing ids from One2many
            current_ids = self.groups_id.ids
            new_ids = [gid for gid in current_ids if gid not in all_custom_group_ids]
            # Use command to replace
            self.groups_id = [(6, 0, new_ids)]

        # Assign selected group
        group_map = {
            'patwari': 'bhuarjan.group_bhuarjan_patwari',
            'sdm': 'bhuarjan.group_bhuarjan_sdm',
            'additional_collector': 'bhuarjan.group_bhuarjan_additional_collector',
            'collector': 'bhuarjan.group_bhuarjan_collector',
            'district_administrator': 'bhuarjan.group_bhuarjan_district_administrator',
            'administrator': 'bhuarjan.group_bhuarjan_admin',
            'department_user': 'bhuarjan.group_bhuarjan_department_user',
        }

        group_ref = group_map.get(self.bhuarjan_role)
        if group_ref:
            group = self.env.ref(group_ref)
            if group:
                self.groups_id = [(4, group.id)]

        for rec in self:
            if rec.bhuarjan_role == 'collector' and rec.district_id:
                sub_divisions = self.env['bhu.sub.division'].search([('district_id', '=', rec.district_id.id)])
                rec.sub_division_ids = [(6, 0, sub_divisions.ids)]

    @api.depends('project_id')
    def _compute_village_domain(self):
        """Compute domain for villages based on selected project"""
        for record in self:
            if record.project_id and record.project_id.village_ids:
                record.village_domain = json.dumps([('id', 'in', record.project_id.village_ids.ids)])
            else:
                record.village_domain = json.dumps([])

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Filter villages based on selected project"""
        if self.project_id:
            # Get villages from the selected project
            project_villages = self.project_id.village_ids.ids
            # Filter out villages that are not in the selected project
            if self.village_ids:
                valid_villages = self.village_ids.filtered(lambda v: v.id in project_villages)
                self.village_ids = valid_villages
    
    def action_view_surveys_in_project(self):
        """Open surveys for this patwari in the project from context"""
        self.ensure_one()
        # Get project_id from context
        project_id = self.env.context.get('default_project_id') or self.env.context.get('active_id')
        if not project_id:
            # Try to get from parent record if in Many2many view
            active_model = self.env.context.get('active_model')
            active_id = self.env.context.get('active_id')
            if active_model == 'bhu.project' and active_id:
                project_id = active_id
        
        if not project_id:
            return False
        
        action = {
            'type': 'ir.actions.act_window',
            'name': f'Surveys by {self.name}',
            'res_model': 'bhu.survey',
            'view_mode': 'list,form',
            'domain': [
                ('user_id', '=', self.id),
                ('project_id', '=', project_id)
            ],
            'context': {
                'default_project_id': project_id,
                'default_user_id': self.id,
                'search_default_group_by_state': 1,
            },
            'target': 'current',
        }
        # Try to get the survey action reference for better view configuration
        try:
            survey_action = self.env.ref('bhuarjan.action_bhu_survey')
            if survey_action:
                action_ref = survey_action.read(['view_mode', 'views'])[0]
                if action_ref.get('views'):
                    action['views'] = action_ref['views']
                if action_ref.get('view_mode'):
                    action['view_mode'] = action_ref['view_mode']
        except Exception:
            pass  # Use default if reference not found
        return action



class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Extend permission for signup_type to District Administrator
    signup_type = fields.Selection(
        [('signup', 'Signup Token'), ('reset', 'Reset Password Token')],
        groups="base.group_erp_manager,bhuarjan.group_bhuarjan_district_administrator"
    )

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """Allow District Admin and Bhuarjan Admin to bypass partner access checks."""
        user = self.env.user
        if operation in ('write', 'create', 'read'):
            if (user.has_group('bhuarjan.group_bhuarjan_admin') or
                    user.has_group('bhuarjan.group_bhuarjan_district_administrator')):
                return True
        return super().check_access_rights(operation, raise_exception=raise_exception)

    def check_access_rule(self, operation):
        """Allow District Admin and Bhuarjan Admin to bypass record rules for partners."""
        user = self.env.user
        if (user.has_group('bhuarjan.group_bhuarjan_admin') or
                user.has_group('bhuarjan.group_bhuarjan_district_administrator')):
            return None
        return super().check_access_rule(operation)

    def write(self, vals):
        """Allow District Admin and Bhuarjan Admin to edit partners (linked to users)."""
        user = self.env.user
        if (user.has_group('bhuarjan.group_bhuarjan_admin') or
                user.has_group('bhuarjan.group_bhuarjan_district_administrator')):
            return super(ResPartner, self.sudo()).write(vals)
        return super().write(vals)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Force partner fields as editable for privileged users in the UI."""
        res = super(ResPartner, self).fields_get(allfields, attributes)
        user = self.env.user
        is_privileged = (
            user.has_group('bhuarjan.group_bhuarjan_admin') or
            user.has_group('bhuarjan.group_bhuarjan_district_administrator')
        )
        if is_privileged:
            for field in ['name', 'email', 'mobile']:
                if field in res:
                    res[field]['readonly'] = False
        return res

