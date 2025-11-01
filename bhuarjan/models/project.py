from odoo import models, fields
import uuid

class BhuProject(models.Model):
    _name = 'bhu.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    project_uuid = fields.Char(string='Project UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    code = fields.Char(string='Project Code', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    budget = fields.Float(string='Budget', tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    village_ids = fields.Many2many('bhu.village.line', string="Villages", tracking=True)
    
    # Company field for multi-company support
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company, tracking=True)