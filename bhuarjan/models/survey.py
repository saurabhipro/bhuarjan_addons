from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid
import logging
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


class Survey(models.Model):
    _name = 'bhu.survey'
    _description = 'Survey (सर्वे)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # Show latest surveys first everywhere (kanban, list, search)
    _order = 'create_date desc, id desc'

    # Basic Information
    user_id = fields.Many2one('res.users', string="User", default=lambda self : self.env.user.id, readonly=True)
    name = fields.Char(string='Survey Number', required=True, tracking=True, readonly=True, copy=False, default='New')
    survey_uuid = fields.Char(string='Survey UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम का नाम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True, tracking=True)
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and filter villages to only those mapped to the project"""
        if self.project_id:
            # Reset village if it's not in the project's villages
            if self.village_id and self.village_id not in self.project_id.village_ids:
                self.village_id = False
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            return {'domain': {'village_id': []}}
    district_name = fields.Char(string='District / जिला', default='Raigarh (Chhattisgarh)', readonly=True, tracking=True)
    survey_date = fields.Date(string='Survey Date / सर्वे दिनाँक', required=True, tracking=True, default=fields.Date.today)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # Single Khasra Details - One survey per khasra
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True, tracking=True)
    total_area = fields.Float(string='Total Area (Hectares) / कुल क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    acquired_area = fields.Float(string='Acquired Area (Hectares) / अर्जन हेतु प्रस्तावित क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    has_traded_land = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Traded Land / व्यापारित भूमि है', default='no', tracking=True,
                                      help='Indicates if the land has been traded')
    traded_land_area = fields.Float(string='Traded Land Area (Hectares) / व्यापारित भूमि क्षेत्रफल (हेक्टेयर)', 
                                    digits=(10, 4), tracking=True, default=0.0,
                                    help='Area of land that has been traded in hectares')
    
    # Land Details
    crop_type_id = fields.Many2one('bhu.land.type', string='Crop Type / फसल का प्रकार', tracking=True,
                                    help='Select the crop type from the land type master (एक फसली, दो फसली, पड़ती)')
    
    irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई का प्रकार', default='irrigated', tracking=True)
    
    # Tree Lines - Detailed tree information
    tree_line_ids = fields.One2many('bhu.survey.tree.line', 'survey_id', 
                                    string='Tree Details / वृक्ष विवरण')
    
    # Separated tree lines by type
    fruit_bearing_tree_line_ids = fields.One2many('bhu.survey.tree.line', 'survey_id',
                                                   string='Fruit-bearing Trees / फलदार वृक्ष',
                                                   domain="[('tree_type', '=', 'fruit_bearing')]")
    non_fruit_bearing_tree_line_ids = fields.One2many('bhu.survey.tree.line', 'survey_id',
                                                       string='Non-fruit-bearing Trees / गैर-फलदार वृक्ष',
                                                       domain="[('tree_type', '=', 'non_fruit_bearing')]")
    
    photo_ids = fields.One2many('bhu.survey.photo', 'survey_id', 
                                string='Photos / फोटो', 
                                help='Photos uploaded for this survey with tags')
    
    # House Details
    has_house = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has House / घर है', default='no', tracking=True)
    house_type = fields.Selection([
        ('kaccha', 'कच्चा'),
        ('pakka', 'पक्का')
    ], string='House Type / घर का प्रकार', tracking=True)
    house_area = fields.Float(string='House Area (Sq. Ft.) / घर का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    has_shed = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Shed / शेड है', default='no', tracking=True)
    shed_area = fields.Float(string='Shed Area (Sq. Ft.) / शेड का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    has_well = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Well / कुआं है', default='no', tracking=True)
    well_type = fields.Selection([
        ('kaccha', 'कच्चा'),
        ('pakka', 'पक्का')
    ], string='Well Type / कुएं का प्रकार', default='kaccha', required=False, tracking=True)
    has_tubewell = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Tubewell/Submersible Pump / ट्यूबवेल/सम्बमर्शिबल पम्प', default='no', tracking=True)
    has_pond = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Pond / तालाब है', default='no', tracking=True)
    
    # Multiple Landowners
    landowner_ids = fields.Many2many('bhu.landowner', 'bhu_survey_landowner_rel', 
                                   'survey_id', 'landowner_id', string='Landowners / भूमिस्वामी', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / अनुमोदित'),
        ('rejected', 'Rejected / अस्वीकृत'),
        ('locked', 'Locked / लॉक')
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # Track submission date
    submitted_date = fields.Datetime(string='Submitted Date / प्रस्तुत दिनांक', readonly=True, tracking=True,
                                     help='Date and time when the survey was submitted for approval')
    
    # Computed fields for list view
    landowner_count = fields.Integer(string='Landowners Count / भूमिस्वामी संख्या', compute='_compute_landowner_count', store=True)
    
    pending_since = fields.Char(string='Pending Since / लंबित', compute='_compute_pending_since', store=False,
                                help='How long the survey has been pending for approval')
    
    @api.depends('landowner_ids')
    def _compute_landowner_count(self):
        """Compute the count of landowners"""
        for record in self:
            record.landowner_count = len(record.landowner_ids)
    
    @api.depends('state', 'submitted_date', 'write_date')
    def _compute_pending_since(self):
        """Compute how long the survey has been pending for approval"""
        for record in self:
            if record.state == 'submitted' and record.submitted_date:
                # Calculate time difference
                # Odoo stores datetimes as naive (UTC), so we compare naive datetimes
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                submitted = record.submitted_date
                # Ensure submitted is naive datetime
                if submitted.tzinfo is not None:
                    submitted = submitted.replace(tzinfo=None)
                
                delta = now - submitted
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                
                if days > 0:
                    record.pending_since = f"{days} day{'s' if days > 1 else ''} ago"
                elif hours > 0:
                    record.pending_since = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif minutes > 0:
                    record.pending_since = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    record.pending_since = "Just now"
            else:
                record.pending_since = ''
    
    # Notification 4 Generation
    notification4_generated = fields.Boolean(string='Notification 4 Generated / अधिसूचना 4 जेनरेट', default=False, tracking=True)
    
    # Computed fields for Form 10 report
    is_single_crop = fields.Boolean(string='Is Single Crop', compute='_compute_crop_fields', store=False)
    is_double_crop = fields.Boolean(string='Is Double Crop', compute='_compute_crop_fields', store=False)
    is_irrigated = fields.Boolean(string='Is Irrigated', compute='_compute_irrigation_fields', store=False)
    is_unirrigated = fields.Boolean(string='Is Unirrigated', compute='_compute_irrigation_fields', store=False)
    
    # Tree counts by development stage (for PDF reports)
    undeveloped_tree_count = fields.Integer(string='Undeveloped Tree Count', compute='_compute_tree_counts_by_stage', store=False)
    semi_developed_tree_count = fields.Integer(string='Semi-developed Tree Count', compute='_compute_tree_counts_by_stage', store=False)
    fully_developed_tree_count = fields.Integer(string='Fully Developed Tree Count', compute='_compute_tree_counts_by_stage', store=False)
    
    @api.depends('crop_type_id')
    def _compute_crop_fields(self):
        for record in self:
            if record.crop_type_id:
                # Check if it's single crop or double crop based on land type code or name
                crop_code = record.crop_type_id.code or ''
                crop_name = record.crop_type_id.name or ''
                record.is_single_crop = 'SINGLE_CROP' in crop_code or 'एक फसली' in crop_name
                record.is_double_crop = 'DOUBLE_CROP' in crop_code or 'दो फसली' in crop_name
            else:
                record.is_single_crop = False
                record.is_double_crop = False
    
    @api.depends('irrigation_type')
    def _compute_irrigation_fields(self):
        for record in self:
            record.is_irrigated = record.irrigation_type == 'irrigated'
            record.is_unirrigated = record.irrigation_type == 'unirrigated'
    
    @api.depends('tree_line_ids', 'tree_line_ids.tree_type', 'tree_line_ids.development_stage', 'tree_line_ids.quantity')
    def _compute_tree_counts_by_stage(self):
        """Compute tree counts by development stage for non-fruit-bearing trees"""
        for record in self:
            undeveloped_count = 0
            semi_developed_count = 0
            fully_developed_count = 0
            
            # Ensure tree_line_ids are loaded
            if record.tree_line_ids:
                for line in record.tree_line_ids:
                    if line.tree_type == 'non_fruit_bearing':
                        if line.development_stage == 'undeveloped':
                            undeveloped_count += line.quantity or 0
                        elif line.development_stage == 'semi_developed':
                            semi_developed_count += line.quantity or 0
                        elif line.development_stage == 'fully_developed':
                            fully_developed_count += line.quantity or 0
            
            record.undeveloped_tree_count = undeveloped_count
            record.semi_developed_tree_count = semi_developed_count
            record.fully_developed_tree_count = fully_developed_count
    
    def get_qr_code_data(self):
        """Generate QR code data for the survey"""
        try:
            import qrcode
            import io
            import base64
            
            # Generate QR code with project UUID and village UUID
            # Format: https://bhuarjan.com/bhuarjan/form10/{project_uuid}/{village_uuid}/download
            # Ensure UUIDs exist and are UNIQUE - generate if missing or duplicate
            if not self.project_id.project_uuid:
                self.project_id.write({'project_uuid': str(uuid.uuid4())})
            
            # Check for duplicate village UUIDs - regenerate if found
            if not self.village_id.village_uuid:
                self.village_id.write({'village_uuid': str(uuid.uuid4())})
            else:
                # Verify this UUID is unique to this village
                duplicate_villages = self.env['bhu.village'].search([
                    ('village_uuid', '=', self.village_id.village_uuid),
                    ('id', '!=', self.village_id.id)
                ])
                if duplicate_villages:
                    # UUID is duplicated - regenerate it
                    self.village_id.write({'village_uuid': str(uuid.uuid4())})
            
            project_uuid = self.project_id.project_uuid
            village_uuid = self.village_id.village_uuid
            qr_url = f"https://bhuarjan.com/bhuarjan/form10/{project_uuid}/{village_uuid}/download"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=2,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
        except ImportError:
            return None
        except Exception:
            return None
   


    # Survey Images and Location
    survey_image = fields.Binary(string='Survey Image / सर्वे छवि', help='Photo taken during survey')
    survey_image_filename = fields.Char(string='Image Filename / छवि फ़ाइल नाम', tracking=True)
    latitude = fields.Float(string='Latitude / अक्षांश', digits=(10, 8), help='GPS Latitude coordinate', tracking=True)
    longitude = fields.Float(string='Longitude / देशांतर', digits=(11, 8), help='GPS Longitude coordinate', tracking=True)
    location_accuracy = fields.Float(string='Location Accuracy (meters) / स्थान सटीकता (मीटर)', digits=(8, 2), help='GPS accuracy in meters', tracking=True)
    location_timestamp = fields.Datetime(string='Location Timestamp / स्थान समय', help='When the GPS coordinates were captured', tracking=True)
    
    # Attachments removed per request

    # Remarks
    remarks = fields.Text(string='Remarks / टिप्पणी', tracking=True)
    
    def name_get(self):
        """Override name_get to include khasra number when called from Section 15 objections"""
        result = []
        show_khasra = self.env.context.get('show_khasra', False)
        
        for record in self:
            name = record.name or 'New'
            if show_khasra and record.khasra_number:
                name = f"{name} - Khasra: {record.khasra_number}"
            result.append((record.id, name))
        return result
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate automatic survey numbers using bhuarjan settings master"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Check if project_id is available
                if vals.get('project_id'):
                    project = self.env['bhu.project'].browse(vals['project_id'])
                    project_code = project.code or project.name or 'PROJ'
                    
                    # Check if sequence settings exist for survey process (global settings, no project dependency)
                    sequence_settings = self.env['bhuarjan.sequence.settings'].search([
                        ('process_name', '=', 'survey'),
                        ('active', '=', True)
                    ], limit=1)
                    
                    if sequence_settings:
                        # Get village_id if available
                        village_id = vals.get('village_id')
                        
                        # Generate sequence number using settings master (placeholders already replaced)
                        sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                            'survey', vals['project_id'], village_id=village_id
                        )
                        if sequence_number:
                            vals['name'] = sequence_number
                        else:
                            # Fallback to default naming if sequence generation fails
                            sequence = self.env['ir.sequence'].next_by_code('bhu.survey') or '001'
                            vals['name'] = f'SC_{project_code}_{sequence.zfill(3)}'
                    else:
                        # No sequence settings found, use fallback naming
                        sequence = self.env['ir.sequence'].next_by_code('bhu.survey') or '001'
                        vals['name'] = f'SC_{project_code}_{sequence.zfill(3)}'
                else:
                    # No project_id, use default naming
                    sequence = self.env['ir.sequence'].next_by_code('bhu.survey') or '001'
                    vals['name'] = f'SC_PROJ_{sequence.zfill(3)}'
        
        records = super(Survey, self).create(vals_list)
        # Log creation
        for record in records:
            record.message_post(
                body=_('Survey created by %s') % self.env.user.name,
                message_type='notification'
            )
        return records
    
    def unlink(self):
        """Override unlink to reset sequence counter after deletion"""
        # Store project_id and village_id before deletion
        project_village_map = {}
        for record in self:
            if record.project_id and record.village_id:
                key = (record.project_id.id, record.village_id.id)
                if key not in project_village_map:
                    project_village_map[key] = {
                        'project_id': record.project_id.id,
                        'village_id': record.village_id.id,
                        'project_code': record.project_id.code or record.project_id.name or 'PROJ',
                        'village_code': record.village_id.village_code if record.village_id.village_code else '',
                    }
        
        # Delete the records
        result = super(Survey, self).unlink()
        
        # After deletion, update sequence counters for affected project+village combinations
        for key, info in project_village_map.items():
            self._reset_sequence_after_deletion(
                info['project_id'],
                info['village_id'],
                info['project_code'],
                info['village_code']
            )
        
        return result
    
    def _reset_sequence_after_deletion(self, project_id, village_id, project_code, village_code):
        """Reset sequence counter based on highest remaining sequence number"""
        # Check if sequence settings exist
        sequence_setting = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', 'survey'),
            ('active', '=', True)
        ], limit=1)
        
        if not sequence_setting:
            return
        
        # Prepare prefix pattern
        sequence_prefix = sequence_setting.prefix.replace('{%PROJ_CODE%}', project_code)
        sequence_prefix = sequence_prefix.replace('{bhu.project.code}', project_code)
        sequence_prefix = sequence_prefix.replace('{PROJ_CODE}', project_code)
        sequence_prefix = sequence_prefix.replace('{bhu.village.code}', village_code)
        
        # Get the last sequence number from existing records
        next_seq_number = self.env['bhuarjan.settings.master']._get_last_sequence_number(
            'bhu.survey',
            sequence_prefix,
            project_id=project_id,
            village_id=village_id,
            initial_seq=sequence_setting.initial_sequence
        )
        
        # Update the ir.sequence counter
        sequence_code = f'bhuarjan.survey.{project_id}.{village_id}'
        ir_sequence = self.env['ir.sequence'].search([
            ('code', '=', sequence_code)
        ], limit=1)
        
        if ir_sequence:
            # Set counter to next_seq_number (which is already last + 1)
            ir_sequence.write({'number_next': next_seq_number})
    
    @api.constrains('khasra_number', 'village_id')
    def _check_unique_khasra_per_village(self):
        """Ensure only one survey per khasra number in one village"""
        for survey in self:
            if survey.khasra_number and survey.village_id:
                existing_surveys = self.search([
                    ('id', '!=', survey.id),
                    ('village_id', '=', survey.village_id.id),
                    ('khasra_number', '=', survey.khasra_number)
                ])
                if existing_surveys:
                    raise ValidationError(_('Khasra number %s already exists in village %s in another survey.') % 
                                        (survey.khasra_number, survey.village_id.name))

    # Business validations
    @api.constrains('total_area', 'acquired_area')
    def _check_areas_positive_and_relation(self):
        for rec in self:
            # both areas must be strictly greater than zero
            if rec.total_area is None or rec.total_area <= 0:
                raise ValidationError(_('Total Area must be greater than 0.'))
            if rec.acquired_area is None or rec.acquired_area <= 0:
                raise ValidationError(_('Acquired Area must be greater than 0.'))
            # acquired cannot exceed total
            if rec.acquired_area > rec.total_area:
                raise ValidationError(_('Acquired Area cannot be greater than Total Area.'))

    @api.constrains('landowner_ids')
    def _check_landowners_present(self):
        for rec in self:
            if not rec.landowner_ids:
                raise ValidationError(_('At least one landowner is required on the survey.'))

    def action_submit(self):
        """Submit the survey for approval"""
        for record in self:
            if not record.khasra_number:
                raise ValidationError(_('Please enter khasra number before submitting.'))
            record.state = 'submitted'
            # Store submission date (as naive datetime for Odoo compatibility)
            record.submitted_date = datetime.now(timezone.utc).replace(tzinfo=None)
            # Log the submission
            record.message_post(
                body=_('Survey submitted for approval by %s') % self.env.user.name,
                message_type='notification'
            )

            # Send email notification to the user
            template = self.env.ref("bhuarjan.email_bhuarjan_survey_submit_form", raise_if_not_found=False)
            if template and record.user_id:
                # Get email from partner or user
                partner_email = None
                if record.user_id.partner_id:
                    partner_email = record.user_id.partner_id.email
                if not partner_email:
                    partner_email = record.user_id.email
                
                # Only send if we have a valid email
                if partner_email and '@' in partner_email and partner_email.strip():
                    try:
                        # Render template to check email_to field
                        rendered_values = template._render_template(template.email_to, 'bhu.survey', [record.id])
                        email_to_value = rendered_values.get(record.id, '').strip()
                        
                        if email_to_value and '@' in email_to_value:
                            template.send_mail(record.id, force_send=True)
                            _logger.info(f"Email notification sent for survey {record.name} to {email_to_value}")
                        else:
                            _logger.warning(f"No valid email recipient in template for survey {record.name}")
                    except Exception as e:
                        # Log error but don't fail the submission
                        _logger.warning(f"Failed to send email notification for survey {record.name}: {str(e)}", exc_info=True)
                else:
                    _logger.info(f"Skipping email for survey {record.name}: User {record.user_id.name} does not have a valid email address")

                    
        wiz = self.env['bhu.survey.message.wizard'].create({
            'message': _('Survey Submitted.\nSurvey No: %s') % ', '.join(self.mapped('name'))
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.survey.message.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Information'),
        }

    def action_approve(self):
        """Approve the survey"""
        for record in self:
            record.state = 'approved'
            # Log the approval
            record.message_post(
                body=_('Survey approved by %s') % self.env.user.name,
                message_type='notification'
            )

    def action_reject(self):
        """Reject the survey"""
        for record in self:
            record.state = 'rejected'
            # Log the rejection
            record.message_post(
                body=_('Survey rejected by %s') % self.env.user.name,
                message_type='notification'
            )

    def action_reset_to_draft(self):
        """Reset survey to draft"""
        for record in self:
            record.state = 'draft'
            # Log the reset
            record.message_post(
                body=_('Survey reset to draft by %s') % self.env.user.name,
                message_type='notification'
            )

    def action_download_form10(self):
        """Download Form-10 as PDF"""
        # Use bulk table report for all selected records (works for single or multiple)
        report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
        return report_action.report_action(self)

    def action_bulk_download_form10(self):
        """Download one PDF containing all visible surveys in a table layout.
        - 10 rows per page, signature section at the end.
        """
        # Respect current user's visibility (patwari: own + assigned villages)
        if self.env.user.bhuarjan_role == 'patwari':
            domain = ['|', ('user_id', '=', self.env.user.id), ('village_id', 'in', self.env.user.village_ids.ids)]
        else:
            domain = []

        all_records = self.search(domain)
        # Use consolidated single-PDF table report
        report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
        return report_action.report_action(all_records)

    def action_download_award_letter(self):
        """Download Award Letter as PDF"""
        for record in self:
            # Generate PDF report
            report_action = self.env.ref('bhuarjan.action_report_award_letter')
            return report_action.report_action(record)

    def action_bulk_download_award_letter(self):
        """Download Award Letter PDFs for all selected surveys"""
        if not self:
            raise ValidationError(_('Please select at least one survey to download.'))
        
        # Generate PDF report for all selected surveys
        report_action = self.env.ref('bhuarjan.action_report_award_letter')
        return report_action.report_action(self)

    def action_form10_preview(self):
        """Preview all Form-10s in a single scrollable HTML view"""
        # Get all surveys for the current user based on their role
        if self.env.user.bhuarjan_role == 'patwari':
            # Patwari can only see their own surveys and surveys from their assigned villages
            domain = [
                '|',
                ('user_id', '=', self.env.user.id),
                ('village_id', 'in', self.env.user.village_ids.ids)
            ]
        else:
            # Other users can see all surveys
            domain = []
        
        # Get all surveys that have Form-10 data
        surveys = self.env['bhu.survey'].search(domain)
        
        if not surveys:
            raise ValidationError(_('No surveys found to preview.'))
        
        # Generate HTML report for all surveys (inline view)
        report_action = self.env.ref('bhuarjan.action_report_form10_bulk_table')
        report_action.report_type = 'qweb-html'
        return report_action.report_action(surveys)




    def log_survey_activity(self, activity_type, details=None):
        """Log custom survey activities"""
        for record in self:
            message = _('Survey activity: %s') % activity_type
            if details:
                message += _(' - %s') % details
            record.message_post(
                body=message,
                message_type='notification'
            )
    
    landowner_pan_numbers = fields.Char(
        string="PAN Numbers",
        compute="_compute_landowner_pan_numbers",
        store=True,
        search="_search_landowner_pan_numbers"
    )

    def _compute_landowner_pan_numbers(self):
        for rec in self:
            if rec.landowner_ids:
                pan_numbers = [
                    str(pan or '') for pan in rec.landowner_ids.mapped('pan_number') if pan
                ]
                rec.landowner_pan_numbers = ', '.join(pan_numbers)
            else:
                rec.landowner_pan_numbers = ''


    landowner_aadhar_numbers = fields.Char(
        string="Aadhaar Numbers",
        compute="_compute_landowner_aadhar_numbers",
        store=True,
        search="_search_landowner_aadhar_numbers"
    )

    def _compute_landowner_aadhar_numbers(self):
        for rec in self:
            if rec.landowner_ids:
                aadhar_numbers = [
                    str(aadhar).strip() for aadhar in rec.landowner_ids.mapped('aadhar_number') if aadhar
                ]
                rec.landowner_aadhar_numbers = ', '.join(aadhar_numbers)
            else:
                rec.landowner_aadhar_numbers = ''


class SurveyTreeLine(models.Model):
    _name = 'bhu.survey.tree.line'
    _description = 'Survey Tree Line / सर्वे वृक्ष लाइन'
    _order = 'development_stage, tree_master_id'

    survey_id = fields.Many2one('bhu.survey', string='Survey / सर्वे', required=True, ondelete='cascade')
    tree_master_id = fields.Many2one('bhu.tree.master', string='Tree / वृक्ष', required=True,
                                     help='Select tree from master')
    
    @api.onchange('tree_type')
    def _onchange_tree_type(self):
        """Update tree_master_id when tree_type changes"""
        # Allow any tree to be selected - no domain restriction
        return {}
    
    @api.onchange('tree_master_id')
    def _onchange_tree_master_id(self):
        """Set default development_stage when tree is selected"""
        if self.tree_master_id:
            # tree_type is computed, so it will update automatically
            # Set default development_stage if not already set
            if not self.development_stage:
                self.development_stage = self._context.get('default_development_stage', 'undeveloped')
    
    @api.model_create_multi
    def create(self, vals_list):
        """tree_type is computed, so it will be set automatically"""
        return super().create(vals_list)
    
    def write(self, vals):
        """tree_type is computed, so it will be updated automatically"""
        return super().write(vals)
    development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित')
    ], string='Development Stage / विकास स्तर', default='undeveloped',
       help='Development stage of the tree. Optional for all tree types.')
    girth_cm = fields.Float(string='Girth (cm) / छाती (से.मी.)', digits=(10, 2),
                            help='Tree trunk girth (circumference) in centimeters. Optional for non-fruit-bearing trees.')
    quantity = fields.Integer(string='Quantity / मात्रा', required=True, default=1,
                             help='Number of trees of this type')
    
    # Tree type - automatically comes from tree master
    tree_type = fields.Selection([
        ('fruit_bearing', 'Fruit-bearing / फलदार'),
        ('non_fruit_bearing', 'Non-fruit-bearing / गैर-फलदार')
    ], string='Tree Type / वृक्ष प्रकार', 
       compute='_compute_tree_type', store=True, readonly=True,
       help='Automatically set from selected tree')
    
    @api.depends('tree_master_id.tree_type')
    def _compute_tree_type(self):
        """Compute tree_type from tree_master_id"""
        for record in self:
            if record.tree_master_id:
                record.tree_type = record.tree_master_id.tree_type
            else:
                record.tree_type = False

    @api.constrains('tree_master_id')
    def _check_tree_master(self):
        """Ensure tree master is selected"""
        for record in self:
            if not record.tree_master_id:
                raise ValidationError(_('Tree must be selected'))
    
    @api.constrains('girth_cm')
    def _check_girth_positive(self):
        """Ensure girth is positive if provided"""
        for record in self:
            # girth_cm is optional - only validate if it's actually a positive number
            # Skip validation if girth_cm is False, None, or 0.0 (means "not set")
            girth_value = record.girth_cm
            if girth_value is False or girth_value is None:
                # Not set - that's fine, it's optional
                pass
            elif girth_value == 0.0:
                # 0.0 means not set for optional fields - that's fine
                pass
            else:
                # girth_cm is provided - validate it's a positive number
                try:
                    girth_float = float(girth_value)
                    if girth_float <= 0:
                        raise ValidationError('Girth (cm) must be greater than 0 if provided.')
                except (ValueError, TypeError):
                    # If it's not a valid number, that's an error
                    raise ValidationError('Girth (cm) must be a valid number if provided.')
    
    @api.constrains('quantity')
    def _check_quantity_positive(self):
        """Ensure quantity is positive"""
        for record in self:
            if record.quantity and record.quantity <= 0:
                raise ValidationError(_('Tree quantity must be greater than 0.'))


class SurveyLine(models.Model):
    _name = 'bhu.survey.line'
    _description = 'Survey Line (सर्वे लाइन)'
    _order = 'khasra_number'

    survey_id = fields.Many2one('bhu.survey', string='Survey', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / प्रभावित खसरा क्रमांक', required=True)
    total_area = fields.Float(string='Total Area (Hectares) / कुल रकबा (हे.में.)', required=True, digits=(10, 4))
    acquired_area = fields.Float(string='Acquired Area (Hectares) / अर्जन हेतु प्रस्तावित क्षेत्रफल (हे.में.)', required=True, digits=(10, 4))
    landowner_name = fields.Char(string='Landowner Name / भूमिस्वामी का नाम', required=True)
    
    # Land Type / भूमि का प्रकार
    crop_type = fields.Selection([
        ('single', 'Single Crop / एक फसली'),
        ('double', 'Double Crop / दो फसली'),
    ], string='Crop Type / फसल का प्रकार', default='single')
    
    irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई का प्रकार', default='irrigated')
    
    # Trees on Land / भूमि पर स्थित वृक्ष की संख्या
    # Note: tree_development_stage and tree_count have been removed
    # Use tree_line_ids to access tree details with development_stage
    
    # Assets on Land / भूमि पर स्थित परिसंपत्तियों का विवरण
    # House Details
    has_house = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has House / घर है', default='no')
    house_type = fields.Selection([
        ('kaccha', 'Kaccha / कच्चा'),
        ('pakka', 'Pakka / पक्का')
    ], string='House Type / मकान प्रकार')
    house_area = fields.Float(string='House Area (Sq. Ft.) / मकान क्षेत्रफल (वर्गफुट)', digits=(10, 2))
    
    # Shed
    shed_area = fields.Float(string='Shed Area (Sq. Ft.) / शेड क्षेत्रफल (वर्गफुट)', digits=(10, 2))
    
    # Well
    has_well = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Well / कुँआ है', default='no')
    well_type = fields.Selection([
        ('kaccha', 'Kaccha / कच्चा'),
        ('pakka', 'Pakka / पक्का')
    ], string='Well Type / कुँआ प्रकार')
    
    # Tubewell/Submersible Pump
    has_tubewell = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Tubewell/Submersible Pump / ट्यूबवेल/सम्बमर्शिबल पम्प', default='no')
    
    # Pond
    has_pond = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Pond / तालाब है', default='no')
    
    # Remarks
    remarks = fields.Text(string='Remarks / रिमार्क')
    
    @api.constrains('acquired_area', 'total_area')
    def _check_area_validation(self):
        """Validate that acquired area is not more than total area"""
        for line in self:
            if line.acquired_area > line.total_area:
                raise ValidationError(_('Acquired area cannot be more than total area for Khasra %s') % line.khasra_number)
    
    @api.constrains('has_house', 'house_type', 'house_area')
    def _check_house_details(self):
        """Validate house details"""
        for line in self:
            if line.has_house == 'yes':
                if not line.house_type:
                    raise ValidationError(_('House type is required when house exists for Khasra %s') % line.khasra_number)
                if not line.house_area:
                    raise ValidationError(_('House area is required when house exists for Khasra %s') % line.khasra_number)
    
    @api.constrains('has_well', 'well_type')
    def _check_well_details(self):
        """Validate well details"""
        for line in self:
            if line.has_well == 'yes' and not line.well_type:
                raise ValidationError(_('Well type is required when well is present for Khasra %s') % line.khasra_number)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to validate sequence settings and generate sequence number"""
        for vals in vals_list:
            # Get project_id and village_id from survey_id if available
            project_id = None
            village_id = None
            if vals.get('survey_id'):
                survey = self.env['bhu.survey'].browse(vals['survey_id'])
                project_id = survey.project_id.id if survey.project_id else None
                village_id = survey.village_id.id if survey.village_id else None
            
            # Check if sequence settings exist for survey process (global settings, no project dependency)
            if project_id:
                sequence_settings = self.env['bhuarjan.sequence.settings'].search([
                    ('process_name', '=', 'survey'),
                    ('active', '=', True)
                ])
                
                if not sequence_settings:
                    raise ValidationError(_(
                        'Sequence settings for Survey process are not defined in Settings Master for project "%s". '
                        'Please configure sequence settings before creating surveys.'
                    ) % self.env['bhu.project'].browse(project_id).name)
                
                # Generate sequence number if name is 'New'
                if vals.get('name', 'New') == 'New':
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'survey', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        raise ValidationError(_(
                            'Failed to generate sequence number for Survey process. '
                            'Please check sequence settings configuration.'
                        ))
        
        return super().create(vals_list)
    
    @api.model
    def check_sequence_settings(self, project_id):
        """Check if sequence settings are available for survey process (global settings, no project dependency)"""
        sequence_settings = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', 'survey'),
            ('active', '=', True)
        ], limit=1)
        
        if not sequence_settings:
            project_name = self.env['bhu.project'].browse(project_id).name
            return {
                'available': False,
                'message': _(
                    'Sequence settings for Survey process are not defined in Settings Master for project "%s". '
                    'Please configure sequence settings before creating surveys.'
                ) % project_name
            }
        
        return {
            'available': True,
            'message': _('Sequence settings are properly configured for Survey process.')
        }

    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        """Override search to apply role-based filtering for Patwari users"""
        # Apply role-based domain filtering
        if self.env.user.bhuarjan_role == 'patwari':
            # Patwari can only see their own surveys and surveys from their assigned villages
            patwari_domain = [
                '|',  # OR condition
                ('user_id', '=', self.env.user.id),  # Their own surveys
                ('village_id', 'in', self.env.user.village_ids.ids)  # Surveys from their assigned villages
            ]
            args = patwari_domain + args
        
        return super(Survey, self)._search(args, offset=offset, limit=limit, order=order)
    
    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        """Check sequence settings when survey is changed"""
        if self.survey_id and self.survey_id.project_id:
            sequence_check = self.check_sequence_settings(self.survey_id.project_id.id)
            if not sequence_check['available']:
                return {
                    'warning': {
                        'title': _('Sequence Settings Not Configured'),
                        'message': sequence_check['message']
                    }
                }