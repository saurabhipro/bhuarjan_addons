# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChannelMaster(models.Model):
    _name = 'bhu.channel.master'
    _description = 'Channel Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Channel Name / चैनल का नाम', required=True, tracking=True)
    channel_type = fields.Selection([
        ('web', 'Web / वेब'),
        ('mobile', 'Mobile / मोबाइल')
    ], string='Channel Type / चैनल प्रकार', required=True, default='web', tracking=True)
    active = fields.Boolean(string='Active / सक्रिय', default=True, tracking=True,
                           help='If unchecked, users cannot login through this channel')
    description = fields.Text(string='Description / विवरण', tracking=True)
    code = fields.Char(string='Channel Code / चैनल कोड', tracking=True,
                      help='Unique code for the channel')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Channel code must be unique!')
    ]

    @api.model
    def create(self, vals):
        """Generate code if not provided"""
        if not vals.get('code'):
            # Generate code from name
            name = vals.get('name', '')
            code = ''.join([c.upper() for c in name if c.isalnum()])[:10]
            if code:
                # Ensure uniqueness
                existing = self.search([('code', '=', code)])
                if existing:
                    code = f"{code}{len(existing) + 1}"
                vals['code'] = code
        return super(ChannelMaster, self).create(vals)

