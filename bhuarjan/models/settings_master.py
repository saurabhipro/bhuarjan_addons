from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class BhuarjanSequenceSettings(models.Model):
    _name = 'bhuarjan.sequence.settings'
    _description = 'Bhuarjan Sequence Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('post_award_payment', 'Post Award Payment'),
        ('payment_reconciliation', 'Payment Reconciliation'),
    ], string='Process Name', required=True)
    
    prefix = fields.Char(string='Prefix', required=True, help='Prefix for sequence number (e.g., SC_{%PROJ_CODE%}_ or SC_{bhu.project.code}_{bhu.village.code}_)')
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
    
    @api.constrains('prefix')
    def _check_prefix_format(self):
        """Validate prefix format for Odoo sequences"""
        for record in self:
            if record.prefix:
                # Check for invalid characters that Odoo sequences don't support
                invalid_chars = ['(', ')', '[', ']', '?', '*', '+', '^', '$', '|', '\\']
                for char in invalid_chars:
                    if char in record.prefix:
                        raise ValidationError(f"Invalid character '{char}' in prefix. Only template placeholders like {{%PROJ_CODE%}} or {{bhu.project.code}} are allowed.")
                
                # Check if prefix is too long (Odoo sequences have limits)
                if len(record.prefix) > 50:
                    raise ValidationError("Prefix is too long. Maximum 50 characters allowed.")
                
                # Check if prefix contains only template placeholders and basic characters
                import re
                if not re.match(r'^[A-Za-z0-9_{}%\.\s_\-]*$', record.prefix):
                    raise ValidationError("Prefix contains invalid characters. Only letters, numbers, underscores, hyphens, dots, spaces, and template placeholders like {{%PROJ_CODE%}} or {{bhu.project.code}} are allowed.")
                
                # Validate template placeholder format
                if '{' in record.prefix and '}' in record.prefix:
                    # Check for valid template placeholders
                    valid_placeholders = ['{%PROJ_CODE%}', '{bhu.project.code}', '{PROJ_CODE}', '{bhu.village.code}']
                    import re
                    placeholder_pattern = r'\{[^}]+\}'
                    placeholders = re.findall(placeholder_pattern, record.prefix)
                    for placeholder in placeholders:
                        if placeholder not in valid_placeholders:
                            raise ValidationError(f"Invalid template placeholder '{placeholder}'. Valid placeholders are: {', '.join(valid_placeholders)}")
    
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
        
        # Prepare prefix for Odoo sequence (replace project placeholders only)
        # Village placeholders will be replaced at runtime when sequence is used
        project_code = self.project_id.code or self.project_id.name or 'PROJ'
        sequence_prefix = self.prefix.replace('{%PROJ_CODE%}', project_code)
        sequence_prefix = sequence_prefix.replace('{bhu.project.code}', project_code)
        sequence_prefix = sequence_prefix.replace('{PROJ_CODE}', project_code)
        # Note: {bhu.village.code} is left as-is and will be replaced at runtime
        
        # Check if sequence already exists
        existing_sequence = self.env['ir.sequence'].search([
            ('code', '=', sequence_code)
        ])
        
        if existing_sequence:
            # Update existing sequence
            existing_sequence.write({
                'prefix': sequence_prefix,
                'number_next': self.initial_sequence,
                'padding': self.padding,
            })
        else:
            # Create new sequence
            self.env['ir.sequence'].create({
                'name': f'Bhuarjan {self.process_name.title()} Sequence - Project {self.project_id.name}',
                'code': sequence_code,
                'prefix': sequence_prefix,
                'number_next': self.initial_sequence,
                'padding': self.padding,
                'company_id': False,
            })
        
        # Also ensure the sequence is properly configured
        sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
        if sequence:
            # Force update to ensure correct format
            sequence.write({
                'prefix': sequence_prefix,
                'number_next': self.initial_sequence,
                'padding': self.padding,
            })


class BhuarjanWorkflowSettings(models.Model):
    _name = 'bhuarjan.workflow.settings'
    _description = 'Bhuarjan Workflow Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('post_award_payment', 'Post Award Payment'),
        ('payment_reconciliation', 'Payment Reconciliation'),
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
    def _get_last_sequence_number(self, model_name, prefix_pattern, project_id=None, village_id=None, initial_seq=1):
        """Get the last sequence number used for a project+village combination
        
        Args:
            model_name: Name of the model (e.g., 'bhu.survey')
            prefix_pattern: Expected prefix pattern (e.g., 'SC_PROJ01_JR_')
            project_id: Project ID to filter records
            village_id: Village ID to filter records
            initial_seq: Starting sequence number if no records exist
            
        Returns:
            int: Last sequence number + 1, or initial_seq if no records exist
        """
        # Build domain to find existing records
        domain = [('name', '!=', 'New'), ('name', '!=', False)]
        if project_id:
            domain.append(('project_id', '=', project_id))
        if village_id:
            domain.append(('village_id', '=', village_id))
        
        # Get all existing records matching the criteria
        model = self.env[model_name]
        existing_records = model.search(domain)
        
        # Extract sequence numbers from existing names
        sequence_numbers = []
        prefix_escaped = re.escape(prefix_pattern)
        # Pattern to match: prefix followed by digits at the end
        pattern = re.compile(rf'^{prefix_escaped}(\d+)$')
        
        for record in existing_records:
            if record.name and pattern.match(record.name):
                match = pattern.match(record.name)
                seq_num = int(match.group(1))
                sequence_numbers.append(seq_num)
        
        # If no existing sequences, return initial sequence
        if not sequence_numbers:
            return initial_seq
        
        # Return the highest sequence number + 1
        return max(sequence_numbers) + 1
    
    @api.model
    def get_sequence_number(self, process_name, project_id, village_id=None):
        """Get next sequence number for a process
        
        If village_id is provided, creates separate sequences per village
        so each village starts from the initial sequence (typically 1).
        The next number is based on the last existing sequence number for that village.
        """
        # First, try to get sequence from settings master
        sequence_setting = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', process_name),
            ('project_id', '=', project_id),
            ('active', '=', True)
        ], limit=1)
        
        if sequence_setting:
            # Get project code for substitution
            project = self.env['bhu.project'].browse(project_id)
            project_code = project.code or project.name or 'PROJ'
            
            # Get village code for substitution if village_id is provided
            village_code = ''
            if village_id:
                village = self.env['bhu.village'].browse(village_id)
                village_code = village.village_code if village.exists() else ''
            
            # Prepare prefix with all placeholders replaced
            sequence_prefix = sequence_setting.prefix.replace('{%PROJ_CODE%}', project_code)
            sequence_prefix = sequence_prefix.replace('{bhu.project.code}', project_code)
            sequence_prefix = sequence_prefix.replace('{PROJ_CODE}', project_code)
            sequence_prefix = sequence_prefix.replace('{bhu.village.code}', village_code)
            
            # Determine sequence code - include village_id if provided for separate counters
            if village_id:
                sequence_code = f'bhuarjan.{process_name}.{project_id}.{village_id}'
            else:
                sequence_code = f'bhuarjan.{process_name}.{project_id}'
            
            # Get last sequence number from existing records (for survey process with village)
            next_seq_number = None
            if process_name == 'survey' and village_id:
                model_name = 'bhu.survey'
                next_seq_number = self._get_last_sequence_number(
                    model_name,
                    sequence_prefix,
                    project_id=project_id,
                    village_id=village_id,
                    initial_seq=sequence_setting.initial_sequence
                )
            
            # Check if sequence exists, if not create it
            existing_sequence = self.env['ir.sequence'].search([
                ('code', '=', sequence_code)
            ], limit=1)
            
            # If we calculated next_seq_number from existing records, use it directly
            if next_seq_number is not None:
                # Update or create the sequence with the calculated number
                if not existing_sequence:
                    # Create new sequence starting from calculated number
                    # Set number_next to next_seq_number + 1 since we'll use next_seq_number now
                    existing_sequence = self.env['ir.sequence'].create({
                        'name': f'Bhuarjan {process_name.title()} Sequence - Project {project.name}' + 
                               (f' - Village {village.name}' if village_id and village.exists() else ''),
                        'code': sequence_code,
                        'prefix': sequence_prefix,
                        'number_next': next_seq_number + 1,  # Set to +1 since we're using next_seq_number now
                        'padding': sequence_setting.padding,
                        'company_id': False,
                    })
                else:
                    # Update existing sequence counter to use the calculated number
                    existing_sequence.write({'number_next': next_seq_number + 1})  # Set to +1 since we're using next_seq_number now
                
                # Generate the sequence number directly using the calculated value
                sequence_number = f"{sequence_prefix}{str(next_seq_number).zfill(sequence_setting.padding)}"
                return sequence_number
            
            # If no next_seq_number calculated, use ir.sequence as normal
            if not existing_sequence:
                # Create new sequence for this project-village combination
                self.env['ir.sequence'].create({
                    'name': f'Bhuarjan {process_name.title()} Sequence - Project {project.name}' + 
                           (f' - Village {village.name}' if village_id and village.exists() else ''),
                    'code': sequence_code,
                    'prefix': sequence_prefix,
                    'number_next': sequence_setting.initial_sequence,
                    'padding': sequence_setting.padding,
                    'company_id': False,
                })
            
            # Get next sequence number from ir.sequence
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            
            if sequence:
                # Replace any remaining placeholders (shouldn't be needed but safety check)
                sequence = sequence.replace('{%PROJ_CODE%}', project_code)
                sequence = sequence.replace('{bhu.project.code}', project_code)
                sequence = sequence.replace('{PROJ_CODE}', project_code)
                sequence = sequence.replace('{bhu.village.code}', village_code)
                return sequence
            else:
                # Fallback: generate sequence using settings master format
                seq_num = sequence_setting.initial_sequence
                sequence_number = f"{sequence_setting.prefix}{str(seq_num).zfill(sequence_setting.padding)}"
                # Substitute placeholders in the generated sequence
                sequence_number = sequence_number.replace('{%PROJ_CODE%}', project_code)
                sequence_number = sequence_number.replace('{bhu.project.code}', project_code)
                sequence_number = sequence_number.replace('{PROJ_CODE}', project_code)
                sequence_number = sequence_number.replace('{bhu.village.code}', village_code)
                # Update the initial sequence for next time (only if no village-specific sequence)
                if not village_id:
                    sequence_setting.write({
                        'initial_sequence': sequence_setting.initial_sequence + 1
                    })
                return sequence_number
        
        # If no settings found, try ir.sequence as last resort
        if village_id:
            sequence_code = f'bhuarjan.{process_name}.{project_id}.{village_id}'
        else:
            sequence_code = f'bhuarjan.{process_name}.{project_id}'
        sequence = self.env['ir.sequence'].next_by_code(sequence_code)
        
        return sequence
    
    @api.model
    def recreate_sequence(self, process_name, project_id):
        """Manually recreate sequence for debugging"""
        sequence_setting = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', process_name),
            ('project_id', '=', project_id),
            ('active', '=', True)
        ], limit=1)
        
        if sequence_setting:
            sequence_setting._create_sequence()
            return True
        return False
    
    @api.model
    def fix_existing_sequences(self, process_name, project_id):
        """Fix existing sequences that might have placeholders"""
        sequence_setting = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', process_name),
            ('project_id', '=', project_id),
            ('active', '=', True)
        ], limit=1)
        
        if sequence_setting:
            # Get project code
            project = self.env['bhu.project'].browse(project_id)
            project_code = project.code or project.name or 'PROJ'
            
            # Recreate the sequence with proper substitution
            sequence_code = f'bhuarjan.{process_name}.{project_id}'
            existing_sequence = self.env['ir.sequence'].search([
                ('code', '=', sequence_code)
            ])
            
            if existing_sequence:
                # Update the sequence with properly substituted prefix
                # Note: Village placeholders are replaced at runtime
                sequence_prefix = sequence_setting.prefix.replace('{%PROJ_CODE%}', project_code)
                sequence_prefix = sequence_prefix.replace('{bhu.project.code}', project_code)
                sequence_prefix = sequence_prefix.replace('{PROJ_CODE}', project_code)
                
                existing_sequence.write({
                    'prefix': sequence_prefix,
                    'number_next': sequence_setting.initial_sequence,
                    'padding': sequence_setting.padding,
                })
                return True
        return False
    
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
