from odoo import models, fields

class BhuProject(models.Model):
    _name = 'bhu.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True)
    code = fields.Char(string='Project Code')
    description = fields.Text(string='Description')
    budget = fields.Float(string='Budget')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    village_ids = fields.Many2many('bhu.village.line', string="Villages")
