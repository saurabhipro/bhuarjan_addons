from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json

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
    state_id = fields.Many2one('res.country.state', string='State', domain=lambda self: self._get_state_domain())
    district_id = fields.Many2one('bhu.district', string='District / जिला')
    sub_division_ids = fields.Many2many('bhu.sub.division', string='Sub Division / उपभाग')
    tehsil_ids = fields.Many2many('bhu.tehsil', string='Tehsil / तहसील')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', 
                                 help='Select a project to filter villages. Only villages from this project will be shown.')
    village_domain = fields.Char(string='Village Domain', compute='_compute_village_domain', store=False)
    village_ids = fields.Many2many('bhu.village', string="Villages")
    bhuarjan_role = fields.Selection([
        ('patwari', 'Patwari'),
        ('revenue_inspector', 'Revenue Inspector'),
        ('nayab_tahsildar', 'Nayab Tahsildar'),
        ('tahsildar', 'Tahsildar'),
        ('sdm', 'SDM'),
        ('additional_collector', 'Additional Collector'),
        ('collector', 'Collector'),
        ('district_administrator', 'District Administrator'),
        ('administrator', 'Administrator'),
        ('sia_team_member', 'SIA Team Member'),
        ('department_user', 'Department User'),
        ('banker', 'Banker'),
    ], string="Bhuarjan Role", default=False)


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
            self.env.ref('bhuarjan.group_bhuarjan_ri').id,
            self.env.ref('bhuarjan.group_bhuarjan_nayab_tahsildar').id,
            self.env.ref('bhuarjan.group_bhuarjan_tahsildar').id,
            self.env.ref('bhuarjan.group_bhuarjan_sdm').id,
            self.env.ref('bhuarjan.group_bhuarjan_additional_collector').id,
            self.env.ref('bhuarjan.group_bhuarjan_collector').id,
            self.env.ref('bhuarjan.group_bhuarjan_district_administrator').id,
            self.env.ref('bhuarjan.group_bhuarjan_admin').id,
            self.env.ref('bhuarjan.group_bhuarjan_sia_team_member').id,
            self.env.ref('bhuarjan.group_bhuarjan_department_user').id,
        ]
        if self.groups_id:
            self.groups_id = [(3, gid) for gid in all_custom_group_ids if gid in self.groups_id.ids]

        # Assign selected group
        group_map = {
            'patwari': 'bhuarjan.group_bhuarjan_patwari',
            'revenue_inspector': 'bhuarjan.group_bhuarjan_ri',
            'nayab_tahsildar': 'bhuarjan.group_bhuarjan_nayab_tahsildar',
            'tahsildar': 'bhuarjan.group_bhuarjan_tahsildar',
            'sdm': 'bhuarjan.group_bhuarjan_sdm',
            'additional_collector': 'bhuarjan.group_bhuarjan_additional_collector',
            'collector': 'bhuarjan.group_bhuarjan_collector',
            'district_administrator': 'bhuarjan.group_bhuarjan_district_administrator',
            'administrator': 'bhuarjan.group_bhuarjan_admin',
            'sia_team_member': 'bhuarjan.group_bhuarjan_sia_team_member',
            'department_user': 'bhuarjan.group_bhuarjan_department_user',
            'banker': 'bhuarjan.group_bhuarjan_banker',
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

