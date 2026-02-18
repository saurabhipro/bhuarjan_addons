from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import requests


class BhuarjanSequenceSettings(models.Model):
    _name = 'bhuarjan.sequence.settings'
    _description = 'Bhuarjan Sequence Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('section4_notification', 'Section 4 Notification'),
        ('section11_notification', 'Section 11 Notification'),
        ('section19_notification', 'Section 19 Notification'),
        ('section15_objection', 'Section 15 Objection'),
        ('draft_award', 'Draft Award'),
        ('payment_file', 'Payment File'),
        ('payment_reconciliation', 'Payment Reconciliation'),
        ('post_award_payment', 'Post Award Payment'),
    ], string='Process Name', required=True)
    
    prefix = fields.Char(string='Prefix', required=True, help='Prefix for sequence number (e.g., SC_{%PROJ_CODE%}_ or SC_{bhu.project.code}_{bhu.village.code}_)')
    initial_sequence = fields.Integer(string='Initial Sequence', default=1, help='Starting number for sequence')
    padding = fields.Integer(string='Padding', default=4, help='Number of digits for sequence (e.g., 4 for 0001)')
    settings_master_id = fields.Many2one('bhuarjan.settings.master', string='Settings Master', required=True)
    active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    _sql_constraints = [
        ('unique_process', 'unique(process_name)', 
         'Sequence settings must be unique per process!')
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
    
    @api.depends('process_name')
    def _compute_display_name(self):
        for record in self:
            if record.process_name and record.process_name in dict(record._fields['process_name'].selection):
                process_label = dict(record._fields['process_name'].selection)[record.process_name]
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
        """Create or update sequence for this setting
        Note: Sequences are created dynamically per project+village when get_sequence_number is called.
        This method is kept for backward compatibility but doesn't create sequences here.
        """
        # Sequences are now created dynamically in get_sequence_number method
        # No need to create sequences at settings creation time
        pass


class BhuarjanWorkflowSettings(models.Model):
    _name = 'bhuarjan.workflow.settings'
    _description = 'Bhuarjan Workflow Settings'
    _rec_name = 'display_name'

    process_name = fields.Selection([
        ('survey', 'Survey'),
        ('form10', 'Form 10'),
        ('section4_notification', 'Section 4 Notification'),
        ('section11_notification', 'Section 11 Notification'),
        ('section19_notification', 'Section 19 Notification'),
        ('section15_objection', 'Section 15 Objection'),
        ('draft_award', 'Draft Award'),
        ('payment_file', 'Payment File'),
        ('payment_reconciliation', 'Payment Reconciliation'),
        ('post_award_payment', 'Post Award Payment'),
    ], string='Process Name', required=True)
    
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
    
    @api.depends('process_name')
    def _compute_display_name(self):
        for record in self:
            if record.process_name and record.process_name in dict(record._fields['process_name'].selection):
                process_label = dict(record._fields['process_name'].selection)[record.process_name]
                record.display_name = process_label
            else:
                record.display_name = "Workflow Settings"
    
    # Removed uniqueness constraint to allow multiple workflow settings per process/project
    # This enables multiple makers for the same workflow


class BhuarjanEscalationMatrix(models.Model):
    _name = 'bhuarjan.escalation.matrix'
    _description = 'Bhuarjan Escalation Matrix'
    _rec_name = 'display_name'
    _order = 'sequence, from_process, to_process'

    sequence = fields.Integer(string='Sequence / क्रम', default=10, required=True,
                             help='Sequence number to order the process flow steps')
    from_process = fields.Selection([
        ('form10', 'Form 10'),
        ('sia_approval', 'SIA Approval'),
        ('section4_notification', 'Section 4 Notification'),
        ('expert_committee', 'Expert Committee Report'),
        ('section11_notification', 'Section 11 Notification'),
        ('section15_objection', 'Section 15 Objection'),
        ('section19_notification', 'Section 19 Notification'),
        ('draft_award', 'Draft Award'),
    ], string='From Process / प्रक्रिया से', required=True,
       help='The process/stage that must be completed before the next process can start')
    
    to_process = fields.Selection([
        ('sia_approval', 'SIA Approval'),
        ('section4_notification', 'Section 4 Notification'),
        ('expert_committee', 'Expert Committee Report'),
        ('section11_notification', 'Section 11 Notification'),
        ('section15_objection', 'Section 15 Objection'),
        ('section19_notification', 'Section 19 Notification'),
        ('draft_award', 'Draft Award'),
        ('payment_file', 'Payment File'),
    ], string='To Process / प्रक्रिया तक', required=True,
       help='The next process/stage that should be completed')
    
    days_required = fields.Integer(string='Days Required / आवश्यक दिन', required=True, default=0,
                                   help='Number of days allowed to complete the next process after the previous process is completed')
    
    settings_master_id = fields.Many2one('bhuarjan.settings.master', string='Settings Master', required=True, ondelete='cascade')
    active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    _sql_constraints = [
        ('unique_process_flow', 'unique(from_process, to_process, settings_master_id)', 
         'Escalation matrix entry must be unique for each from-to process combination!'),
        ('unique_sequence', 'unique(sequence, settings_master_id)', 
         'Sequence number must be unique for each settings master!')
    ]
    
    @api.depends('from_process', 'to_process', 'days_required')
    def _compute_display_name(self):
        """Compute display name for escalation matrix entry"""
        for record in self:
            from_label = dict(record._fields['from_process'].selection).get(record.from_process, record.from_process) if record.from_process else ''
            to_label = dict(record._fields['to_process'].selection).get(record.to_process, record.to_process) if record.to_process else ''
            if from_label and to_label:
                record.display_name = f"{from_label} → {to_label} ({record.days_required} days)"
            else:
                record.display_name = "Escalation Matrix"
    
    @api.constrains('from_process', 'to_process')
    def _check_process_flow(self):
        """Validate that from_process and to_process are different"""
        for record in self:
            if record.from_process == record.to_process:
                raise ValidationError('From Process and To Process cannot be the same!')
    
    @api.model
    def get_days_required(self, from_process, to_process):
        """Get days required for a process flow"""
        escalation = self.search([
            ('from_process', '=', from_process),
            ('to_process', '=', to_process),
            ('active', '=', True)
        ], limit=1)
        
        if escalation:
            return escalation.days_required
        return 0  # Default to 0 days if not configured


class BhuarjanSettingsMaster(models.Model):
    _name = 'bhuarjan.settings.master'
    _description = 'Bhuarjan Settings Master'
    _rec_name = 'name'
    
    name = fields.Char(string='Name', default='Bhuarjan Settings', required=True)
    
    # Sequence Settings
    sequence_settings_ids = fields.One2many('bhuarjan.sequence.settings', 'settings_master_id', 
                                          string='Sequence Settings')
    
    # Workflow Settings
    workflow_settings_ids = fields.One2many('bhuarjan.workflow.settings', 'settings_master_id', 
                                           string='Workflow Settings')
    
    # Escalation Matrix
    escalation_matrix_ids = fields.One2many('bhuarjan.escalation.matrix', 'settings_master_id', 
                                           string='Escalation Matrix')
    
    # AWS Configuration
    s3_bucket_name = fields.Char(string='S3 Bucket Name', help='AWS S3 bucket name for storing files')
    aws_region = fields.Char(string='AWS Region', help='AWS region (e.g., ap-south-1, us-east-1)')
    aws_access_key = fields.Char(string='AWS Access Key', help='AWS access key ID')
    aws_secret_key = fields.Char(string='AWS Secret Key', help='AWS secret access key')
    
    # Payment Configuration
    debit_account_number = fields.Char(string='Debit Account Number', help='Default debit account number for payment file generation')
    
    # OTP API Configuration
    otp_api_url = fields.Char(string='OTP API URL', help='Base URL for OTP API service')
    otp_api_key = fields.Char(string='OTP API Key', help='API key for OTP service')

    otp_sender_id = fields.Char(string='OTP Sender ID', help='Sender ID for OTP messages')
    otp_client_id = fields.Char(string='OTP Client ID', help='Client ID for OTP service')
    otp_dlt_template_id = fields.Char(string='DLT Template ID', help='DLT Template ID for OTP messages')
    otp_message_template = fields.Char(string='OTP Message Template', 
                                      default='OTP to Login in Survey APP {otp} Redmelon Pvt Ltd.',
                                      help='Message template. Use {otp} as placeholder for the OTP code')
    
    # Test SMS Configuration
    test_mobile_number = fields.Char(string='Test Mobile Number', help='Mobile number to send test OTP to')
    test_otp = fields.Char(string='Test OTP', help='OTP to send for testing', default='1234')
    api_documentation = fields.Text(string='API Documentation', readonly=True, help='Generated API documentation JSON')
    
    # App Hash for Android Auto-Read
    android_app_hash = fields.Char(string='Android App Hash', help='11-character hash string required for Android SMS Retriever API (e.g., FA+9qCX9VSu)')

    # Static OTP Configuration (for testing/development when SMS API is disabled)
    enable_static_otp = fields.Boolean(string='Enable Static OTP', default=False,
                                      help='If enabled, use static OTP instead of sending SMS. Useful when SMS API is disabled.')
    static_otp_value = fields.Char(string='Static OTP Value', help='Static OTP value to use when static OTP is enabled (e.g., 1234)')
    
    # App Version Check Configuration
    enforce_app_version_check = fields.Boolean(string='Enforce App Version Check', default=False,
                                               help='If enabled, app version check will be enforced. If disabled, version check will be bypassed.')
    latest_app_version = fields.Char(string='Latest App Version', compute='_compute_latest_app_version', 
                                    readonly=True, store=False,
                                    help='Latest active app version from App Version model')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('enforce_app_version_check')
    def _compute_latest_app_version(self):
        """Compute latest app version from app version model"""
        for record in self:
            latest_version = self.env['bhu.app.version'].sudo().get_latest_version()
            if latest_version:
                record.latest_app_version = f"{latest_version.name} (Code: {latest_version.version_code})"
            else:
                record.latest_app_version = "No active version found"
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure only one settings master exists - return existing if found"""
        existing = self.search([], limit=1)
        if existing:
            # If a record already exists, return it instead of creating a new one.
            # This handles both data loading (XML import) and normal operation.
            return existing
        # If no record exists yet, create ONE record using the first vals dict.
        # (even if called with multiple vals, we enforce singleton settings)
        vals = vals_list[0] if vals_list else {}
        return super().create([vals])
    
    @api.model
    def get_settings_master(self):
        """Get the single Bhuarjan Settings master record, create if it doesn't exist"""
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({})
        return settings
    
    @api.constrains('enable_static_otp', 'static_otp_value')
    def _check_static_otp_value(self):
        """Ensure static_otp_value is provided when enable_static_otp is True"""
        for record in self:
            if record.enable_static_otp and not record.static_otp_value:
                raise ValidationError('Static OTP Value is required when Enable Static OTP is checked.')
    
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
        # First, try to get sequence from settings master (global settings, no project dependency)
        sequence_setting = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', process_name),
            ('active', '=', True)
        ], limit=1)
        
        if sequence_setting:
            # Get project code for substitution
            project = self.env['bhu.project'].browse(project_id)
            project_code = project.code or project.name or 'PROJ'
            
            # Get village code for substitution if village_id is provided
            village_code = ''
            if village_id:
                # Ensure village_id is a single integer, not a list or recordset
                if isinstance(village_id, (list, tuple)):
                    village_id = village_id[0] if village_id else None
                elif hasattr(village_id, '__iter__') and not isinstance(village_id, (str, int)):
                    # It's a recordset or iterable, get first ID
                    village_id = village_id[0].id if len(village_id) > 0 else None
                
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
                    existing_sequence = self.env['ir.sequence'].sudo().create({
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
                # Use sudo() to bypass access rights - sequences are system objects
                self.env['ir.sequence'].sudo().create({
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
        """Get workflow users for a process (global settings, no project dependency)"""
        workflow_settings = self.env['bhuarjan.workflow.settings'].search([
            ('process_name', '=', process_name),
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

    def action_test_sms(self):
        """Action to test SMS sending configuration"""
        self.ensure_one()
        
        if not self.test_mobile_number:
            raise ValidationError("Please enter a Test Mobile Number.")
            
        if not self.otp_api_url:
             raise ValidationError("OTP API URL is not configured.")

        if not self.otp_sender_id:
             raise ValidationError("OTP Sender ID is not configured. Please enter the Sender ID (e.g., REDM) in the field.")

        # Logic similar to request_otp in auth.py
        otp_code = self.test_otp or '1234'
        mobile = self.test_mobile_number
        
        # Prepare message
        message_template = self.otp_message_template or 'OTP to Login in Survey APP {otp} Redmelon Pvt Ltd.'
        message = message_template.replace('{otp}', otp_code)
        
        # Append Android App Hash if configured
        if self.android_app_hash:
            message = f"{message} {self.android_app_hash}"
        
        # Prepare parameters
        params = {
            'ApiKey': self.otp_api_key or '',
            'ClientId': self.otp_client_id or '',
            'senderid': self.otp_sender_id or '',
            'message': message,
            'MobileNumbers': mobile,
            'msgtype': 'TXT',
            'response': 'Y',
            'dlttempid': self.otp_dlt_template_id or ''
        }
        
        try:
            # We use verify=False because some SMS gateways have SSL issues or self-signed certs
            # But in production you ideally want ssl valid
            response = requests.get(self.otp_api_url, params=params)
            
            if response.status_code == 200:
                # Generate API documentation after successful test
                self.action_generate_api_docs(response_text=response.text, status_code=response.status_code)
                
                # Check for API-level errors in the JSON response
                try:
                    response_json = response.json()
                    if response_json.get('ErrorCode') and response_json.get('ErrorCode') != 0:
                         # API returned 200 OK but with an application error
                         error_msg = response_json.get('ErrorDescription', 'Unknown API Error')
                         raise ValidationError(f"SMS API Error: {error_msg} (Code: {response_json.get('ErrorCode')})")
                except ValueError:
                    # Response is not JSON, proceed with caution or log it
                    pass

                # Show success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Test SMS sent successfully to {mobile}. Response: {response.text}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise ValidationError(f"Failed to send SMS. Status Code: {response.status_code}. Response: {response.text}")
        except Exception as e:
            raise ValidationError(f"Error sending SMS: {str(e)}")

    def action_generate_api_docs(self, response_text=None, status_code=200):
        """Generate API documentation JSON"""
        self.ensure_one()
        
        # Determine values to use (defaults if not set)
        api_url = self.otp_api_url or 'https://api.example.com/otp'
        api_key = self.otp_api_key or 'YOUR_API_KEY'
        client_id = self.otp_client_id or 'YOUR_CLIENT_ID'
        sender_id = self.otp_sender_id or 'SENDER_ID'
        dlt_template_id = self.otp_dlt_template_id or 'YOUR_DLT_ID'
        
        test_mobile = self.test_mobile_number or '9999999999'
        test_otp = self.test_otp or '1234'
        
        message_template = self.otp_message_template or 'OTP to Login in Survey APP {otp} Redmelon Pvt Ltd.'
        message = message_template.replace('{otp}', test_otp)
        
        # Clean URL to get base path and params separate for clarity
        base_url = api_url.split('?')[0]
        
        documentation = {
            "name": "Send OTP SMS",
            "request": {
                "method": "GET",
                "url": base_url,
                "params": [
                    {"key": "ApiKey", "value": api_key, "description": "API Key provided by service"},
                    {"key": "ClientId", "value": client_id, "description": "Client ID provided by service"},
                    {"key": "senderid", "value": sender_id, "description": "Sender ID (approved via DLT)"},
                    {"key": "message", "value": message, "description": "Message content (must match template)"},
                    {"key": "MobileNumbers", "value": test_mobile, "description": "Comma separated mobile numbers"},
                    {"key": "msgtype", "value": "TXT", "description": "Message type"},
                    {"key": "response", "value": "Y", "description": "Return response"},
                    {"key": "dlttempid", "value": dlt_template_id, "description": "DLT Template ID (mandatory)"}
                ]
            },
            "response": {
                "status_code": status_code,
                "body": response_text or '{"status": "success", "message": "SMS sent successfully"}'
            },
            "curl_example": f"""curl --location --request GET '{base_url}?ApiKey={api_key}&ClientId={client_id}&senderid={sender_id}&message={requests.utils.quote(message)}&MobileNumbers={test_mobile}&msgtype=TXT&response=Y&dlttempid={dlt_template_id}'"""
        }
        
        import json
        self.api_documentation = json.dumps(documentation, indent=4)
        return True
