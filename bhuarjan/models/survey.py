from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


class Survey(models.Model):
    _name = 'bhu.survey'
    _description = 'Survey (सर्वे)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'survey_date desc, name'

    # Basic Information
    user_id = fields.Many2one('res.users', string="User", default=lambda self : self.env.user.id, readonly=True)
    name = fields.Char(string='Survey Number', required=True, tracking=True, readonly=True, copy=False, default='New')
    survey_uuid = fields.Char(string='Survey UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम का नाम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True, tracking=True)
    district_name = fields.Char(string='District / जिला', default='Raigarh (Chhattisgarh)', readonly=True, tracking=True)
    survey_date = fields.Date(string='Survey Date / सर्वे दिनाँक', required=True, tracking=True, default=fields.Date.today)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # Single Khasra Details - One survey per khasra
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True, tracking=True)
    total_area = fields.Float(string='Total Area (Hectares) / कुल क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    acquired_area = fields.Float(string='Acquired Area (Hectares) / अधिग्रहित क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    
    # Land Details
    crop_type = fields.Selection([
        ('single', 'Single Crop / एकल फसल'),
        ('double', 'Double Crop / दोहरी फसल'),
    ], string='Crop Type / फसल का प्रकार', default='single', tracking=True)
    
    irrigation_type = fields.Selection([
        ('irrigated', 'Irrigated / सिंचित'),
        ('unirrigated', 'Unirrigated / असिंचित'),
    ], string='Irrigation Type / सिंचाई का प्रकार', default='irrigated', tracking=True)
    
    # Tree Details
    tree_development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully developed / पूर्ण विकसित')
    ], string='Tree Development Stage / वृक्ष विकास स्तर', tracking=True)
    tree_count = fields.Integer(string='Number of Trees / वृक्षों की संख्या', default=0, tracking=True)
    
    # House Details
    house_type = fields.Selection([
        ('kachcha', 'कच्चा'),
        ('pucca', 'पक्का')
    ], string='House Type / घर का प्रकार', tracking=True)
    house_area = fields.Float(string='House Area (Sq. Ft.) / घर का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    shed_area = fields.Float(string='Shed Area (Sq. Ft.) / शेड का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    has_well = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Well / कुआं है', default='no', tracking=True)
    well_type = fields.Selection([
        ('kachcha', 'कच्चा'),
        ('pakka', 'पक्का')
    ], string='Well Type / कुएं का प्रकार', default='kachcha', required=True, tracking=True)
    has_tubewell = fields.Selection([
        ('yes', 'Yes / हाँ'),
        ('no', 'No / नहीं'),
    ], string='Has Tubewell/Submersible Pump / ट्यूबवेल/सम्बमर्शिबल पम्प', default='no', tracking=True)
    trees_description = fields.Text(string='Trees Description / वृक्षों का विवरण', tracking=True, 
                                   help='Detailed description of trees present on the land')
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
    
    # Notification 4 Generation
    notification4_generated = fields.Boolean(string='Notification 4 Generated / अधिसूचना 4 जेनरेट', default=False, tracking=True)
    
    # Computed fields for Form 10 report
    is_single_crop = fields.Boolean(string='Is Single Crop', compute='_compute_crop_fields', store=False)
    is_double_crop = fields.Boolean(string='Is Double Crop', compute='_compute_crop_fields', store=False)
    is_irrigated = fields.Boolean(string='Is Irrigated', compute='_compute_irrigation_fields', store=False)
    is_unirrigated = fields.Boolean(string='Is Unirrigated', compute='_compute_irrigation_fields', store=False)
    
    @api.depends('crop_type')
    def _compute_crop_fields(self):
        for record in self:
            record.is_single_crop = record.crop_type == 'single'
            record.is_double_crop = record.crop_type == 'double'
    
    @api.depends('irrigation_type')
    def _compute_irrigation_fields(self):
        for record in self:
            record.is_irrigated = record.irrigation_type == 'irrigated'
            record.is_unirrigated = record.irrigation_type == 'unirrigated'
   


    # Survey Images and Location
    survey_image = fields.Binary(string='Survey Image / सर्वे छवि', help='Photo taken during survey')
    survey_image_filename = fields.Char(string='Image Filename / छवि फ़ाइल नाम', tracking=True)
    latitude = fields.Float(string='Latitude / अक्षांश', digits=(10, 8), help='GPS Latitude coordinate', tracking=True)
    longitude = fields.Float(string='Longitude / देशांतर', digits=(11, 8), help='GPS Longitude coordinate', tracking=True)
    location_accuracy = fields.Float(string='Location Accuracy (meters) / स्थान सटीकता (मीटर)', digits=(8, 2), help='GPS accuracy in meters', tracking=True)
    location_timestamp = fields.Datetime(string='Location Timestamp / स्थान समय', help='When the GPS coordinates were captured', tracking=True)
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments / संलग्नक', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate automatic survey numbers using bhuarjan settings master"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Check if project_id is available
                if vals.get('project_id'):
                    project = self.env['bhu.project'].browse(vals['project_id'])
                    project_code = project.code or project.name or 'PROJ'
                    
                    # Check if sequence settings exist for survey process
                    sequence_settings = self.env['bhuarjan.sequence.settings'].search([
                        ('process_name', '=', 'survey'),
                        ('project_id', '=', vals['project_id']),
                        ('active', '=', True)
                    ])
                    
                    if sequence_settings:
                        # Generate sequence number using settings master
                        sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                            'survey', vals['project_id']
                        )
                        if sequence_number:
                            # Replace all project code placeholders with actual project code
                            survey_number = sequence_number.replace('{%PROJ_CODE%}', project_code)
                            survey_number = survey_number.replace('{bhu.project.code}', project_code)
                            survey_number = survey_number.replace('{PROJ_CODE}', project_code)
                            vals['name'] = survey_number
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

    def action_submit(self):
        """Submit the survey for approval"""
        for record in self:
            if not record.khasra_number:
                raise ValidationError(_('Please enter khasra number before submitting.'))
            record.state = 'submitted'
            # Log the submission
            record.message_post(
                body=_('Survey submitted for approval by %s') % self.env.user.name,
                message_type='notification'
            )

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
        for record in self:
            # Generate PDF report
            report_action = self.env.ref('bhuarjan.action_report_form10_survey')
            return report_action.report_action(record)

    def action_bulk_download_form10(self):
        """Download Form-10 PDFs for all selected surveys"""
        if not self:
            raise ValidationError(_('Please select at least one survey to download.'))
        
        # Generate PDF report for all selected surveys
        report_action = self.env.ref('bhuarjan.action_report_form10_survey')
        return report_action.report_action(self)

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
        report_action = self.env.ref('bhuarjan.action_report_form10_survey')
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


class SurveyLine(models.Model):
    _name = 'bhu.survey.line'
    _description = 'Survey Line (सर्वे लाइन)'
    _order = 'khasra_number'

    survey_id = fields.Many2one('bhu.survey', string='Survey', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / प्रभावित खसरा क्रमांक', required=True)
    total_area = fields.Float(string='Total Area (Hectares) / कुल रकबा (हे.में.)', required=True, digits=(10, 4))
    acquired_area = fields.Float(string='Acquired Area (Hectares) / कुल अर्जित रकबा (हे.में.)', required=True, digits=(10, 4))
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
    tree_development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्द्ध विकसित'),
        ('fully_developed', 'Fully Developed / पूर्ण विकसित')
    ], string='Tree Development Stage / वृक्ष विकास स्तर', required=True)
    tree_count = fields.Integer(string='Number of Trees / वृक्षों की संख्या', required=True)
    
    # Assets on Land / भूमि पर स्थित परिसंपत्तियों का विवरण
    # House Details
    house_type = fields.Selection([
        ('kachcha', 'Kachcha / कच्चा'),
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
        ('kachcha', 'Kachcha / कच्चा'),
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
    
    @api.constrains('house_type', 'house_area')
    def _check_house_details(self):
        """Validate house details"""
        for line in self:
            if line.house_type and not line.house_area:
                raise ValidationError(_('House area is required when house type is selected for Khasra %s') % line.khasra_number)
    
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
            # Get project_id from survey_id if available
            project_id = None
            if vals.get('survey_id'):
                survey = self.env['bhu.survey'].browse(vals['survey_id'])
                project_id = survey.project_id.id
            
            # Check if sequence settings exist for survey process
            if project_id:
                sequence_settings = self.env['bhuarjan.sequence.settings'].search([
                    ('process_name', '=', 'survey'),
                    ('project_id', '=', project_id),
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
                        'survey', project_id
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
        """Check if sequence settings are available for survey process"""
        sequence_settings = self.env['bhuarjan.sequence.settings'].search([
            ('process_name', '=', 'survey'),
            ('project_id', '=', project_id),
            ('active', '=', True)
        ])
        
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