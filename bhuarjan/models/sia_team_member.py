# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SiaTeamMember(models.Model):
    _name = 'bhu.sia.team.member'
    _description = 'SIA Team Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name / नाम', required=True, tracking=True)
    post = fields.Char(string='Post / पद', tracking=True)
    address = fields.Text(string='Address / पता', tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', tracking=True)
    user_id = fields.Many2one('res.users', string='User / उपयोगकर्ता', tracking=True,
                              help='Link to res.users if this member corresponds to a system user')

