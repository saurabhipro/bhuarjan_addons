from odoo import models, fields, api
from odoo.exceptions import ValidationError

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
    circle_ids = fields.Many2many('bhu.circle', string='Circle / circle')
    village_ids = fields.Many2many('bhu.village', string="Villages")
    bhuarjan_role = fields.Selection([
        ('patwari', 'Patwari'),
        ('revenue_inspector', 'Revenue Inspector'),
        ('nayab_tahsildar', 'Nayab Tahsildar'),
        ('tahsildar', 'Tahsildar'),
        ('sdm', 'SDM'),
        ('additional_collector', 'Additional Collector'),
        ('collector', 'Collector'),
        ('administrator', 'Administrator'),
    ], string="Bhuarjan Role", default=False)


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
            self.env.ref('bhuarjan.group_bhuarjan_admin').id,
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
            'administrator': 'bhuarjan.group_bhuarjan_admin',
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

