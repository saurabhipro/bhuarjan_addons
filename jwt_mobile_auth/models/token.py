from odoo import models, fields

class JWTToken(models.Model):
    _name = 'jwt.token'
    _description = 'JWT Token'

    user_id = fields.Many2one('res.users', string='User', required=True)
    token = fields.Char(string='Token', required=True)
