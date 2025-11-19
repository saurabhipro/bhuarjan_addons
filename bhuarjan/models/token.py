from odoo import models, fields
import datetime

class JWTToken(models.Model):
    _name = 'jwt.token'
    _description = 'JWT Token'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', required=True)
    token = fields.Char(string='Token', required=True)
    channel_id = fields.Many2one('bhu.channel.master', string='Channel', help='Channel through which user logged in')
    channel_type = fields.Selection(related='channel_id.channel_type', store=True, readonly=True, string='Channel Type')
    create_date = fields.Datetime(string='Created On', readonly=True)
