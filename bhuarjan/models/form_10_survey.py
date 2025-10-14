from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


class Form10Survey(models.Model):
    _name = 'form.10.survey'
    _description = 'Form-10 Survey (भू-अर्जन फार्म-10)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'survey_date desc, name'

    # Basic Information
    name = fields.Char(string='Survey Number', required=True, tracking=True, readonly=True, copy=False, default='New')
    survey_uuid = fields.Char(string='Survey UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम का नाम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True, tracking=True)
    district_name = fields.Char(string='District / जिला', default='Raigarh (Chhattisgarh)', readonly=True)
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
    
    # Multiple Landowners
    landowner_ids = fields.Many2many('bhu.landowner', 'form_10_survey_landowner_rel', 
                                   'survey_id', 'landowner_id', string='Landowners / भूमिस्वामी')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / अनुमोदित'),
        ('rejected', 'Rejected / अस्वीकृत')
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments / संलग्नक')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate automatic survey numbers for multiple records"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Get the next sequence number
                sequence = self.env['ir.sequence'].next_by_code('form.10.survey') or '001'
                vals['name'] = f'SUR_{sequence.zfill(3)}'
        return super(Form10Survey, self).create(vals_list)
    
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

    def action_approve(self):
        """Approve the survey"""
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        """Reject the survey"""
        for record in self:
            record.state = 'rejected'

    def action_reset_to_draft(self):
        """Reset survey to draft"""
        for record in self:
            record.state = 'draft'


class Form10SurveyLine(models.Model):
    _name = 'form.10.survey.line'
    _description = 'Form-10 Survey Line (भू-अर्जन फार्म-10 लाइन)'
    _order = 'khasra_number'

    survey_id = fields.Many2one('form.10.survey', string='Survey', required=True, ondelete='cascade')
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
