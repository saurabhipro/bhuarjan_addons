from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


class Survey(models.Model):
    _name = 'bhu.survey'
    _description = 'Survey (सर्वे)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'survey_date desc, name'

    # Basic Information
    name = fields.Char(string='Survey Number', required=True, tracking=True, readonly=True, copy=False, default='New')
    survey_uuid = fields.Char(string='Survey UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम का नाम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True, tracking=True)
    district_name = fields.Char(string='District / जिला', default='Raigarh (Chhattisgarh)', readonly=True, tracking=True)
    survey_date = fields.Date(string='Survey Date / सर्वे दिनाँक', required=True, tracking=True, default=fields.Date.today)
    
    
    # Single Khasra Details - One survey per khasra
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True, tracking=True)
    total_area = fields.Float(string='Total Area (Hectares) / कुल क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    acquired_area = fields.Float(string='Acquired Area (Hectares) / अधिग्रहित क्षेत्रफल (हेक्टेयर)', digits=(10, 4), tracking=True)
    
    # Land Details
    is_single_crop = fields.Boolean(string='Single Crop / एकल फसल', default=False, tracking=True)
    is_double_crop = fields.Boolean(string='Double Crop / दोहरी फसल', default=False, tracking=True)
    is_irrigated = fields.Boolean(string='Irrigated / सिंचित', default=False, tracking=True)
    is_unirrigated = fields.Boolean(string='Unirrigated / असिंचित', default=False, tracking=True)
    
    # Tree Details
    tree_development_stage = fields.Selection([
        ('undeveloped', 'Undeveloped / अविकसित'),
        ('semi_developed', 'Semi-developed / अर्ध-विकसित'),
        ('fully_developed', 'Fully developed / पूर्ण विकसित')
    ], string='Tree Development Stage / वृक्ष विकास स्तर', tracking=True)
    tree_count = fields.Integer(string='Number of Trees / वृक्षों की संख्या', default=0, tracking=True)
    
    # House Details
    house_type = fields.Selection([
        ('kachcha', 'Kachcha / कच्चा'),
        ('pucca', 'Pucca / पक्का'),
        ('semi_pucca', 'Semi-Pucca / अर्ध-पक्का')
    ], string='House Type / घर का प्रकार', tracking=True)
    house_area = fields.Float(string='House Area (Sq. Ft.) / घर का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    shed_area = fields.Float(string='Shed Area (Sq. Ft.) / शेड का क्षेत्रफल (वर्ग फुट)', digits=(10, 2), tracking=True)
    has_well = fields.Boolean(string='Has Well / कुआं है', default=False, tracking=True)
    well_type = fields.Selection([
        ('open', 'Open Well / खुला कुआं'),
        ('bore', 'Bore Well / बोर कुआं'),
        ('hand_pump', 'Hand Pump / हैंड पंप')
    ], string='Well Type / कुएं का प्रकार', tracking=True)
    has_electricity = fields.Boolean(string='Has Electricity / बिजली है', default=False, tracking=True)
    has_road_access = fields.Boolean(string='Has Road Access / सड़क पहुंच है', default=False, tracking=True)
    has_tubewell = fields.Boolean(string='Has Tubewell/Submersible Pump / ट्यूबवेल/सम्बमर्शिबल पम्प', default=False, tracking=True)
    has_pond = fields.Boolean(string='Has Pond / तालाब है', default=False, tracking=True)
    
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
        """Generate automatic survey numbers for multiple records"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Get the next sequence number
                sequence = self.env['ir.sequence'].next_by_code('bhu.survey') or '001'
                vals['name'] = f'SUR_{sequence.zfill(3)}'
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

    def action_capture_location(self):
        """Capture current GPS location using browser geolocation"""
        for record in self:
            # Trigger JavaScript-based location capture
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Location Capture'),
                    'message': _('Please allow location access to capture GPS coordinates. The location will be automatically filled in the form fields.'),
                    'type': 'info',
                }
            }

    def update_location(self, latitude, longitude, accuracy=None):
        """Update GPS coordinates from JavaScript"""
        for record in self:
            record.write({
                'latitude': latitude,
                'longitude': longitude,
                'location_accuracy': accuracy,
                'location_timestamp': fields.Datetime.now()
            })
            # Log location capture
            record.message_post(
                body=_('GPS location captured: Lat: %s, Lon: %s, Accuracy: %s meters') % 
                     (latitude, longitude, accuracy or 'Unknown'),
                message_type='notification'
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Location Updated'),
                    'message': _('GPS coordinates have been captured successfully.'),
                    'type': 'success',
                }
            }

    def action_auto_capture_location(self):
        """Auto-capture GPS location when form loads"""
        for record in self:
            # This method is called by JavaScript when auto-capture is triggered
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Auto Location Capture'),
                    'message': _('GPS location will be automatically captured when you open this form on a mobile device or PWA.'),
                    'type': 'info',
                }
            }

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
    is_single_crop = fields.Boolean(string='Single Crop / एक फसली')
    is_double_crop = fields.Boolean(string='Double Crop / दो फसली')
    is_irrigated = fields.Boolean(string='Irrigated / सिंचित')
    is_unirrigated = fields.Boolean(string='Unirrigated / असिंचित')
    
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
    has_well = fields.Boolean(string='Has Well / कुँआ है')
    well_type = fields.Selection([
        ('kachcha', 'Kachcha / कच्चा'),
        ('pakka', 'Pakka / पक्का')
    ], string='Well Type / कुँआ प्रकार')
    
    # Tubewell/Submersible Pump
    has_tubewell = fields.Boolean(string='Has Tubewell/Submersible Pump / ट्यूबवेल/सम्बमर्शिबल पम्प')
    
    # Pond
    has_pond = fields.Boolean(string='Has Pond / तालाब है')
    
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
            if line.has_well and not line.well_type:
                raise ValidationError(_('Well type is required when well is present for Khasra %s') % line.khasra_number)
