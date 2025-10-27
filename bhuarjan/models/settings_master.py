from odoo import models, fields, api


class BhuarjanSequenceSettings(models.Model):
    _name = 'bhuarjan.sequence.settings'
    _description = 'Bhuarjan Sequence Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('notification4', 'Notification 4'),
        ('section11', 'Section 11'),
        ('section15', 'Section 15'),
        ('post_award_payment', 'Post Award Payment'),
        ('payment_reconciliation', 'Payment Reconciliation'),
        ('jansunwai', 'Jansunwai'),
        ('expert_review', 'Expert Review'),
        ('collector_approval', 'Collector Approval'),
        ('section19', 'Section 19'),
        ('section21', 'Section 21'),
        ('section23', 'Section 23'),
    ], string='Process Name', required=True)
    
    prefix = fields.Char(string='Prefix', required=True, help='Prefix for sequence number (e.g., SUR_)')
    initial_sequence = fields.Integer(string='Initial Sequence', default=1, help='Starting number for sequence')
    padding = fields.Integer(string='Padding', default=4, help='Number of digits for sequence (e.g., 4 for 0001)')
    project_id = fields.Many2one('bhu.project', string='Project', compute='_compute_project_id', store=True)
    settings_master_id = fields.Many2one('bhuarjan.settings.master', string='Settings Master', required=True)
    active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    _sql_constraints = [
        ('unique_process_project', 'unique(process_name, project_id)', 
         'Sequence settings must be unique per process and project!')
    ]
    
    @api.depends('settings_master_id', 'settings_master_id.project_id')
    def _compute_project_id(self):
        for record in self:
            if record.settings_master_id:
                record.project_id = record.settings_master_id.project_id
            else:
                record.project_id = False
    
    @api.depends('process_name', 'project_id')
    def _compute_display_name(self):
        for record in self:
            if record.process_name and record.process_name in dict(record._fields['process_name'].selection):
                process_label = dict(record._fields['process_name'].selection)[record.process_name]
                if record.project_id:
                    record.display_name = f"{process_label} - {record.project_id.name}"
                else:
                    record.display_name = process_label
            else:
                record.display_name = "Sequence Settings"
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically create sequences"""
        records = super().create(vals_list)
        for record in records:
            record._create_sequence()
        return records
    
    def write(self, vals):
        """Override write to update sequences"""
        result = super().write(vals)
        self._create_sequence()
        return result
    
    def _create_sequence(self):
        """Create or update sequence for this setting"""
        if not self.project_id or not self.process_name:
            return
            
        sequence_code = f'bhuarjan.{self.process_name}.{self.project_id.id}'
        
        # Check if sequence already exists
        existing_sequence = self.env['ir.sequence'].search([
            ('code', '=', sequence_code)
        ])
        
        if existing_sequence:
            # Update existing sequence
            existing_sequence.write({
                'prefix': self.prefix,
                'number_next': self.initial_sequence,
                'padding': self.padding,
            })
        else:
            # Create new sequence
            self.env['ir.sequence'].create({
                'name': f'Bhuarjan {self.process_name.title()} Sequence - Project {self.project_id.name}',
                'code': sequence_code,
                'prefix': self.prefix,
                'number_next': self.initial_sequence,
                'padding': self.padding,
                'company_id': False,
            })


class BhuarjanWorkflowSettings(models.Model):
    _name = 'bhuarjan.workflow.settings'
    _description = 'Bhuarjan Workflow Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('notification4', 'Notification 4'),
        ('section11', 'Section 11'),
        ('section15', 'Section 15'),
        ('post_award_payment', 'Post Award Payment'),
        ('payment_reconciliation', 'Payment Reconciliation'),
        ('jansunwai', 'Jansunwai'),
        ('expert_review', 'Expert Review'),
        ('collector_approval', 'Collector Approval'),
        ('section19', 'Section 19'),
        ('section21', 'Section 21'),
        ('section23', 'Section 23'),
    ], string='Process Name', required=True)
    
    project_id = fields.Many2one('bhu.project', string='Project', compute='_compute_project_id', store=True)
    settings_master_id = fields.Many2one('bhuarjan.settings.master', string='Settings Master', required=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Workflow Users
    maker_user_ids = fields.Many2many('res.users', string='Makers', required=True,
                                     help='Users responsible for creating/initiating the process')
    checker_user_id = fields.Many2one('res.users', string='Checker', 
                                     help='User responsible for checking/verifying the process')
    approver_user_id = fields.Many2one('res.users', string='Approver', 
                                      help='User responsible for final approval')
    
    # Additional workflow settings
    require_checker = fields.Boolean(string='Require Checker', default=True,
                                   help='Whether checker approval is mandatory')
    require_approver = fields.Boolean(string='Require Approver', default=True,
                                     help='Whether approver approval is mandatory')
    
    # Email notifications
    notify_maker = fields.Boolean(string='Notify Maker', default=True)
    notify_checker = fields.Boolean(string='Notify Checker', default=True)
    notify_approver = fields.Boolean(string='Notify Approver', default=True)
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('settings_master_id', 'settings_master_id.project_id')
    def _compute_project_id(self):
        for record in self:
            if record.settings_master_id:
                record.project_id = record.settings_master_id.project_id
            else:
                record.project_id = False
    
    @api.depends('process_name', 'project_id')
    def _compute_display_name(self):
        for record in self:
            if record.process_name and record.process_name in dict(record._fields['process_name'].selection):
                process_label = dict(record._fields['process_name'].selection)[record.process_name]
                if record.project_id:
                    record.display_name = f"{process_label} - {record.project_id.name}"
                else:
                    record.display_name = process_label
            else:
                record.display_name = "Workflow Settings"
    
    # Removed uniqueness constraint to allow multiple workflow settings per process/project
    # This enables multiple makers for the same workflow


class BhuarjanSettingsMaster(models.Model):
    _name = 'bhuarjan.settings.master'
    _description = 'Bhuarjan Settings Master'
    _rec_name = 'display_name'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Sequence Settings
    sequence_settings_ids = fields.One2many('bhuarjan.sequence.settings', 'settings_master_id', 
                                          string='Sequence Settings')
    
    # Workflow Settings
    workflow_settings_ids = fields.One2many('bhuarjan.workflow.settings', 'settings_master_id', 
                                           string='Workflow Settings')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('project_id')
    def _compute_display_name(self):
        for record in self:
            if record.project_id:
                record.display_name = f"Settings - {record.project_id.name}"
            else:
                record.display_name = "Settings Master"
    
    @api.model
    def get_sequence_number(self, process_name, project_id):
        """Get next sequence number for a process"""
        sequence_code = f'bhuarjan.{process_name}.{project_id}'
        sequence = self.env['ir.sequence'].next_by_code(sequence_code)
        
        if not sequence:
            # Fallback to settings if sequence doesn't exist
            sequence_setting = self.env['bhuarjan.sequence.settings'].search([
                ('process_name', '=', process_name),
                ('project_id', '=', project_id),
                ('active', '=', True)
            ], limit=1)
            
            if sequence_setting:
                sequence = f"{sequence_setting.prefix}{str(sequence_setting.initial_sequence).zfill(sequence_setting.padding)}"
        
        return sequence
    
    @api.model
    def get_workflow_users(self, process_name, project_id):
        """Get workflow users for a process"""
        workflow_settings = self.env['bhuarjan.workflow.settings'].search([
            ('process_name', '=', process_name),
            ('project_id', '=', project_id),
            ('active', '=', True)
        ])
        
        if not workflow_settings:
            return {}
        
        # Collect all makers from all workflow settings
        all_makers = workflow_settings.mapped('maker_user_ids')
        
        # Use the first workflow setting for other settings (checker, approver, etc.)
        first_setting = workflow_settings[0]
            
        return {
            'makers': all_makers,  # List of all makers
            'maker': all_makers[0] if all_makers else False,  # First maker for backward compatibility
            'checker': first_setting.checker_user_id,
            'approver': first_setting.approver_user_id,
            'require_checker': first_setting.require_checker,
            'require_approver': first_setting.require_approver,
            'notify_maker': first_setting.notify_maker,
            'notify_checker': first_setting.notify_checker,
            'notify_approver': first_setting.notify_approver,
        }
