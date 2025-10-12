from odoo import models, fields

class BhuProject(models.Model):
    _name = 'bhu.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True)
    budget = fields.Float(string='Budget')
