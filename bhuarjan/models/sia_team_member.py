# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SiaTeamMember(models.Model):
    _name = 'bhu.sia.team.member'
    _description = 'SIA Team Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name / नाम', required=True, tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', tracking=True)
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)

