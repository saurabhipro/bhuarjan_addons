# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SiaTeam(models.Model):
    _name = 'bhu.sia.team'
    _description = 'SIA Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Team Name / टीम का नाम', required=True, tracking=True, default='New')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    team_member_ids = fields.Many2many('res.users', string='Team Members / टीम सदस्य', required=True, tracking=True)
    description = fields.Text(string='Description / विवरण', tracking=True)
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True)
    
    @api.model
    def create(self, vals):
        """Generate team name if not provided"""
        if vals.get('name', 'New') == 'New':
            project = self.env['bhu.project'].browse(vals.get('project_id'))
            sequence = self.env['ir.sequence'].next_by_code('bhu.sia.team') or 'New'
            vals['name'] = f'SIA Team - {project.name} - {sequence}'
        return super(SiaTeam, self).create(vals)

