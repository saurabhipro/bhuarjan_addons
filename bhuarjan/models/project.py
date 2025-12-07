from odoo import models, fields, api, _
import uuid

class BhuProject(models.Model):
    _name = 'bhu.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    project_uuid = fields.Char(string='Project UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    
    def action_regenerate_uuid(self):
        """Regenerate UUID for a single project"""
        if not self:
            return
        new_uuid = str(uuid.uuid4())
        # Ensure the new UUID is unique
        while self.env['bhu.project'].search([('project_uuid', '=', new_uuid)]):
            new_uuid = str(uuid.uuid4())
        
        self.write({'project_uuid': new_uuid})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'UUID Regenerated',
                'message': f'New UUID: {new_uuid}',
                'type': 'success',
                'sticky': False,
            }
        }
    code = fields.Char(string='Project Code', tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', tracking=True,
                                    help='Select the department for this project')
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
    
    def action_set_draft(self):
        """Set project status to Draft"""
        self.write({'state': 'draft'})
        return True
    
    def action_set_active(self):
        """Set project status to Active"""
        self.write({'state': 'active'})
        return True
    
    def action_set_completed(self):
        """Set project status to Completed"""
        self.write({'state': 'completed'})
        return True
    
    def action_set_cancelled(self):
        """Set project status to Cancelled"""
        self.write({'state': 'cancelled'})
        return True
    village_ids = fields.Many2many('bhu.village', string="Villages", tracking=True)
    sdm_ids = fields.Many2many('res.users', 'bhu_project_sdm_rel', 'project_id', 'user_id',
                               string="SDM / उप-विभागीय मजिस्ट्रेट", 
                               domain="[('bhuarjan_role', '=', 'sdm')]", tracking=True,
                               help="Select Sub-Divisional Magistrates for this project")
    tehsildar_ids = fields.Many2many('res.users', 'bhu_project_tehsildar_rel', 'project_id', 'user_id',
                                     string="Tehsildar / तहसीलदार", 
                                     domain="[('bhuarjan_role', '=', 'tahsildar')]", tracking=True,
                                     help="Select Tehsildars for this project")
    
    # Company field for multi-company support
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company, tracking=True)
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        """Override search to filter projects by user's assigned projects"""
        # Skip filtering if context flag is set (to avoid recursion)
        if self.env.context.get('skip_project_domain_filter'):
            return super()._search(args, offset=offset, limit=limit, order=order)
        
        # Get current user
        user = self.env.user
        
        # Admin and system users see all projects - no filtering needed
        if not (user.has_group('bhuarjan.group_bhuarjan_admin') or user.has_group('base.group_system')):
            # Get user's assigned projects using sudo() to bypass access rights and context flag to avoid recursion
            assigned_projects = self.sudo().with_context(skip_project_domain_filter=True).search([
                '|',
                ('sdm_ids', 'in', user.id),
                ('tehsildar_ids', 'in', user.id)
            ])
            
            if assigned_projects:
                # Add domain to filter by assigned projects
                args = args + [('id', 'in', assigned_projects.ids)]
            else:
                # No assigned projects, return domain that matches nothing
                args = args + [('id', 'in', [])]
        
        # Call parent search with modified domain
        return super()._search(args, offset=offset, limit=limit, order=order)