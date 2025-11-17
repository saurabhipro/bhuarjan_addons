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
    phone = fields.Char(string='Phone Number / फोन नंबर', tracking=True)
    
    # Company/Organization Information
    company_id = fields.Many2one('res.company', string='Company / कंपनी', required=True, 
                                 default=lambda self: self.env.company, tracking=True)
    
    # Address Information
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', tracking=True)
    district_id = fields.Many2one('bhu.district', string='District / जिला', tracking=True)
    state = fields.Char(string='State / राज्य', default='Chhattisgarh', readonly=True)
    owner_address = fields.Text(string='Owner Address / मालिक का पता', tracking=True,
                                help='Complete address of the landowner')
    
    # Identity Documents
    aadhar_number = fields.Char(string='Aadhar Number / आधार नंबर', tracking=True)
    pan_number = fields.Char(string='PAN Number / पैन नंबर', tracking=True)
    
    # Bank Details
    bank_name = fields.Char(string='Bank Name / बैंक का नाम', tracking=True)
    bank_branch = fields.Char(string='Bank Branch / बैंक शाखा', tracking=True)
    account_number = fields.Char(string='Account Number / खाता संख्या', tracking=True)
    ifsc_code = fields.Char(string='IFSC Code / आईएफएससी कोड', tracking=True)
    account_holder_name = fields.Char(string='Account Holder Name / खाताधारक का नाम', tracking=True)
    
    # Documents
    aadhar_card = fields.Binary(string='Aadhar Card / आधार कार्ड')
    pan_card = fields.Binary(string='PAN Card / पैन कार्ड')
    
    # Survey Relations
    survey_ids = fields.Many2many('bhu.survey', 'bhu_survey_landowner_rel', 
                                 'landowner_id', 'survey_id', string='Related Surveys / संबंधित सर्वे')
    
    # Validation Methods
    
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
    
    @api.onchange('tehsil_id')
    def _onchange_tehsil_id(self):
        if self.tehsil_id:
            self.district_id = self.tehsil_id.district_id
    
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
    
