# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class BhuLandowner(models.Model):
    _name = 'bhu.landowner'
    _description = 'Landowner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    # Basic Information
    name = fields.Char(string='Full Name / पूरा नाम', required=True, tracking=True)
    father_name = fields.Char(string="Father's Name / पिता का नाम", tracking=True)
    mother_name = fields.Char(string="Mother's Name / माता का नाम", tracking=True)
    spouse_name = fields.Char(string="Spouse's Name / पति/पत्नी का नाम", tracking=True)
    
    # Personal Details
    age = fields.Integer(string='Age / आयु', tracking=True)
    gender = fields.Selection([
        ('male', 'Male / पुरुष'),
        ('female', 'Female / महिला'),
        ('other', 'Other / अन्य')
    ], string='Gender / लिंग', tracking=True)
    
    # Contact Information
    mobile = fields.Char(string='Mobile Number / मोबाइल नंबर', tracking=True)
    phone = fields.Char(string='Phone Number / फोन नंबर', tracking=True)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    email = fields.Char(string='Email / ईमेल', tracking=True)
    
    # Address Information
    address_line1 = fields.Char(string='Address Line 1 / पता पंक्ति 1', tracking=True)
    address_line2 = fields.Char(string='Address Line 2 / पता पंक्ति 2', tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    pincode = fields.Char(string='Pincode / पिनकोड', tracking=True)
    state = fields.Char(string='State / राज्य', default='Chhattisgarh', readonly=True)
    
    # Identity Documents
    aadhar_number = fields.Char(string='Aadhar Number / आधार नंबर', tracking=True)
    pan_number = fields.Char(string='PAN Number / पैन नंबर', tracking=True)
    voter_id = fields.Char(string='Voter ID / मतदाता पहचान पत्र', tracking=True)
    ration_card_number = fields.Char(string='Ration Card Number / राशन कार्ड नंबर', tracking=True)
    
    # Bank Details
    bank_name = fields.Char(string='Bank Name / बैंक का नाम', tracking=True)
    bank_branch = fields.Char(string='Bank Branch / बैंक शाखा', tracking=True)
    account_number = fields.Char(string='Account Number / खाता संख्या', tracking=True)
    ifsc_code = fields.Char(string='IFSC Code / आईएफएससी कोड', tracking=True)
    account_holder_name = fields.Char(string='Account Holder Name / खाताधारक का नाम', tracking=True)
    
    # Additional Information
    occupation = fields.Char(string='Occupation / व्यवसाय', tracking=True)
    annual_income = fields.Float(string='Annual Income / वार्षिक आय', digits=(12, 2), tracking=True)
    is_minor = fields.Boolean(string='Is Minor / नाबालिग है', default=False, tracking=True)
    guardian_name = fields.Char(string='Guardian Name / अभिभावक का नाम', tracking=True)
    guardian_relation = fields.Char(string='Guardian Relation / अभिभावक का संबंध', tracking=True)
    
    # Documents and Photos
    photo = fields.Binary(string='Photo / फोटो')
    aadhar_card = fields.Binary(string='Aadhar Card / आधार कार्ड')
    pan_card = fields.Binary(string='PAN Card / पैन कार्ड')
    voter_id_card = fields.Binary(string='Voter ID Card / मतदाता पहचान पत्र')
    ration_card = fields.Binary(string='Ration Card / राशन कार्ड')
    bank_passbook = fields.Binary(string='Bank Passbook / बैंक पासबुक')
    other_documents = fields.Binary(string='Other Documents / अन्य दस्तावेज')
    
    # Survey Relations
    survey_ids = fields.Many2many('bhu.survey', 'bhu_survey_landowner_rel', 
                                 'landowner_id', 'survey_id', string='Related Surveys / संबंधित सर्वे')
    
    # Computed Fields
    full_address = fields.Text(string='Complete Address / पूरा पता', compute='_compute_full_address', store=True)
    
    @api.depends('address_line1', 'address_line2', 'village_id', 'tehsil_id', 'district_id', 'pincode', 'state')
    def _compute_full_address(self):
        for record in self:
            address_parts = []
            if record.address_line1:
                address_parts.append(record.address_line1)
            if record.address_line2:
                address_parts.append(record.address_line2)
            if record.village_id:
                address_parts.append(record.village_id.name)
            if record.tehsil_id:
                address_parts.append(record.tehsil_id.name)
            if record.district_id:
                address_parts.append(record.district_id.name)
            if record.pincode:
                address_parts.append(record.pincode)
            if record.state:
                address_parts.append(record.state)
            record.full_address = ', '.join(address_parts)
    
    # Validation Methods
    @api.constrains('mobile')
    def _check_mobile(self):
        for record in self:
            if record.mobile:
                if not re.match(r'^[6-9]\d{9}$', record.mobile):
                    raise ValidationError('Please enter a valid 10-digit mobile number starting with 6-9.')
    
    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                    raise ValidationError('Please enter a valid email address.')
    
    @api.constrains('aadhar_number')
    def _check_aadhar(self):
        for record in self:
            if record.aadhar_number:
                if not re.match(r'^\d{12}$', record.aadhar_number):
                    raise ValidationError('Aadhar number must be exactly 12 digits.')
    
    @api.constrains('pan_number')
    def _check_pan(self):
        for record in self:
            if record.pan_number:
                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', record.pan_number.upper()):
                    raise ValidationError('PAN number must be in format: ABCDE1234F')
    
    @api.constrains('account_number')
    def _check_account_number(self):
        for record in self:
            if record.account_number:
                if not re.match(r'^\d{9,18}$', record.account_number):
                    raise ValidationError('Account number must be between 9-18 digits.')
    
    @api.constrains('ifsc_code')
    def _check_ifsc(self):
        for record in self:
            if record.ifsc_code:
                if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', record.ifsc_code.upper()):
                    raise ValidationError('IFSC code must be in format: ABCD0123456')
    
    @api.constrains('age')
    def _check_age(self):
        for record in self:
            if record.age and (record.age < 0 or record.age > 120):
                raise ValidationError('Age must be between 0 and 120 years.')
    
    # Auto-fill methods
    @api.onchange('village_id')
    def _onchange_village_id(self):
        if self.village_id:
            self.tehsil_id = self.village_id.tehsil_id
            self.district_id = self.village_id.district_id
            self.pincode = self.village_id.pincode
    
    @api.onchange('tehsil_id')
    def _onchange_tehsil_id(self):
        if self.tehsil_id:
            self.district_id = self.tehsil_id.district_id
    
    @api.onchange('age')
    def _onchange_age(self):
        if self.age and self.age < 18:
            self.is_minor = True
        else:
            self.is_minor = False
    
    def action_view_surveys(self):
        """Action to view related surveys"""
        action = self.env.ref('bhuarjan.action_bhu_survey').read()[0]
        action['domain'] = [('landowner_ids', 'in', self.ids)]
        action['context'] = {'default_landowner_ids': [(6, 0, self.ids)]}
        return action

    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        """Override search to apply role-based filtering for Patwari users"""
        # Apply role-based domain filtering
        if self.env.user.bhuarjan_role == 'patwari':
            # Patwari can only see landowners from their assigned villages
            # and landowners who are in surveys they created
            patwari_domain = [
                '|',  # OR condition
                ('village_id', 'in', self.env.user.village_ids.ids),  # Landowners from their assigned villages
                ('survey_ids.user_id', '=', self.env.user.id)  # Landowners in surveys they created
            ]
            args = patwari_domain + args
        
        return super(BhuLandowner, self)._search(args, offset=offset, limit=limit, order=order)
    
