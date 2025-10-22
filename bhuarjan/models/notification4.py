from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime


class Notification4(models.Model):
    _name = 'bhu.notification4'
    _description = 'Notification 4 (Rule 4)'
    _order = 'notification_date desc, name'
    
    name = fields.Char(string='Notification Number', required=True, readonly=True, copy=False, default='New')
    notification_date = fields.Date(string='Notification Date / अधिसूचना दिनाँक', required=True, default=fields.Date.today)
    
    # Location Information
    district_id = fields.Many2one('bhu.district', string='District / जिला', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)
    
    # Public Purpose
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन का विवरण', required=True)
    
    # Survey Information
    survey_ids = fields.Many2many('bhu.survey', string='Related Surveys / संबंधित सर्वे', 
                                 domain="[('village_id', '=', village_id)]")
    total_area = fields.Float(string='Total Area (Hectares) / कुल क्षेत्रफल (हेक्टेयर)', compute='_compute_total_area', store=True)
    
    # Land Details Table (Auto-generated from surveys)
    land_details_ids = fields.One2many('bhu.notification4.land.detail', 'notification_id', string='Land Details / भूमि विवरण')
    
    # Public Hearing Details
    hearing_date = fields.Date(string='Hearing Date / सुनवाई दिनाँक', tracking=True)
    hearing_time = fields.Char(string='Hearing Time / सुनवाई का समय', tracking=True)
    hearing_location = fields.Char(string='Hearing Location / सुनवाई का स्थान', tracking=True)
    
    # Details from SIA (Social Impact Assessment)
    brief_public_purpose = fields.Text(string='(1) लोक प्रयोजन का संक्षिप्त विवरण।', tracking=True)
    direct_affected_families = fields.Integer(string='(2) प्रत्यक्ष रूप से प्रभावित परिवारों की संख्या।', tracking=True)
    indirect_affected_families = fields.Integer(string='(3) परोक्ष रूप से प्रभावित परिवारों की संख्या।', tracking=True)
    private_assets_count = fields.Integer(string='(4) प्रभावित क्षेत्र में निजी भवनों एवं अन्य परिसंपत्तियों की अनुमानित संख्या।', tracking=True)
    govt_assets_count = fields.Integer(string='(5) प्रभावित क्षेत्र में शासकीय भवनों एवं अन्य परिसंपत्तियों की अनुमानित संख्या।', tracking=True)
    is_acquisition_minimum = fields.Boolean(string='(6) क्या प्रस्तावित अधिग्रहण न्यूनतम है?', tracking=True)
    alternative_site_feasibility = fields.Text(string='(7) संभावित वैकल्पिक स्थल तथा उसकी व्यवहार्यता पर विचार।', tracking=True)
    project_total_cost = fields.Monetary(string='(8) परियोजना की कुल लागत।', currency_field='company_currency_id', tracking=True)
    project_benefits = fields.Text(string='(9) परियोजना से होने वाले लाभ।', tracking=True)
    compensation_framework = fields.Text(string='(10) प्रस्तावित सामाजिक प्रभाव के प्रतिकर की रूपरेखा एवं अनुमानित व्यय।', tracking=True)
    other_affected_factors = fields.Text(string='(11) परियोजना से प्रभावित अन्य कारक।', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('published', 'Published / प्रकाशित'),
        ('cancelled', 'Cancelled / रद्द')
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    # Location for signature
    signature_place = fields.Char(string='Signature Place / हस्ताक्षर स्थान', required=True)
    signature_date = fields.Date(string='Signature Date / हस्ताक्षर दिनाँक', required=True, default=fields.Date.today)
    
    # Company currency
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate automatic notification numbers"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                sequence = self.env['ir.sequence'].next_by_code('bhu.notification4') or '001'
                vals['name'] = f'NOT4_{sequence.zfill(3)}'
        return super(Notification4, self).create(vals_list)
    
    @api.depends('survey_ids', 'survey_ids.total_area')
    def _compute_total_area(self):
        """Compute total area from related surveys"""
        for record in self:
            record.total_area = sum(survey.total_area for survey in record.survey_ids)
    
    @api.onchange('village_id')
    def _onchange_village_id(self):
        """Auto-populate surveys when village is selected"""
        if self.village_id:
            # Get all surveys for the selected village
            surveys = self.env['bhu.survey'].search([
                ('village_id', '=', self.village_id.id),
                ('state', 'in', ['submitted', 'approved'])
            ])
            self.survey_ids = surveys
            self.district_id = self.village_id.district_id
            self.tehsil_id = self.village_id.tehsil_id
            self._generate_land_details()
    
    def _generate_land_details(self):
        """Generate land details table from surveys"""
        for record in self:
            # Clear existing records
            record.land_details_ids.unlink()
            
            if not record.survey_ids:
                return
            
            # Group surveys by khasra number
            khasra_groups = {}
            for survey in record.survey_ids:
                khasra = survey.khasra_number or 'Unknown'
                if khasra not in khasra_groups:
                    khasra_groups[khasra] = {
                        'area': 0,
                        'landowners': set(),
                        'surveys': []
                    }
                khasra_groups[khasra]['area'] += survey.total_area or 0
                khasra_groups[khasra]['landowners'].update(survey.landowner_ids)
                khasra_groups[khasra]['surveys'].append(survey)
            
            # Create land detail records
            for khasra, data in khasra_groups.items():
                try:
                    self.env['bhu.notification4.land.detail'].create({
                        'notification_id': record.id,
                        'khasra_number': khasra,
                        'area': data['area'],
                        'landowner_count': len(data['landowners']),
                        'survey_count': len(data['surveys'])
                    })
                except Exception as e:
                    raise ValidationError(_('Error creating land details: %s') % str(e))
    
    def action_publish(self):
        """Publish the notification"""
        for record in self:
            if not record.survey_ids:
                raise ValidationError(_('Please add at least one survey before publishing.'))
            if not record.land_details_ids:
                raise ValidationError(_('Please generate land details before publishing.'))
            record.state = 'published'
    
    def action_cancel(self):
        """Cancel the notification"""
        for record in self:
            record.state = 'cancelled'
    
    def action_draft(self):
        """Reset to draft"""
        for record in self:
            record.state = 'draft'
    
    def action_generate_land_details(self):
        """Manually generate land details from surveys"""
        for record in self:
            if not record.survey_ids:
                raise ValidationError(_('Please select surveys first.'))
            
            # Debug: Show survey information
            survey_info = []
            for survey in record.survey_ids:
                survey_info.append(f"Survey: {survey.name}, Khasra: {survey.khasra_number}, Area: {survey.total_area}")
            
            # Generate land details
            record._generate_land_details()
            
            # Show success message with details
            message = _('Land details generated successfully for %d khasras.') % len(record.land_details_ids)
            if survey_info:
                message += '\n\nSurveys processed:\n' + '\n'.join(survey_info)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': message,
                    'type': 'success',
                }
            }
    
    def action_populate_surveys(self):
        """Manually populate surveys for the selected village"""
        for record in self:
            if not record.village_id:
                raise ValidationError(_('Please select a village first.'))
            
            # Get all surveys for the village
            surveys = self.env['bhu.survey'].search([
                ('village_id', '=', record.village_id.id),
                ('state', 'in', ['submitted', 'approved']),
                ('notification4_generated', '=', False)
            ])
            
            if not surveys:
                raise ValidationError(_('No available surveys found for this village.'))
            
            # Set the surveys
            record.survey_ids = surveys
            record.district_id = record.village_id.district_id
            record.tehsil_id = record.village_id.tehsil_id
            
            # Generate land details
            record._generate_land_details()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Surveys populated and land details generated for %d surveys.') % len(surveys),
                    'type': 'success',
                }
            }
    
    def action_download_notification(self):
        """Download notification as PDF"""
        for record in self:
            report_action = self.env.ref('bhuarjan.action_report_notification4')
            return report_action.report_action(record)


class Notification4LandDetail(models.Model):
    _name = 'bhu.notification4.land.detail'
    _description = 'Notification 4 Land Details'
    
    notification_id = fields.Many2one('bhu.notification4', string='Notification', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True)
    area = fields.Float(string='Area (Hectares) / क्षेत्रफल (हेक्टेयर)', required=True)
    landowner_count = fields.Integer(string='Number of Landowners / भूमिस्वामियों की संख्या')
    survey_count = fields.Integer(string='Number of Surveys / सर्वे की संख्या')
    
    # Display fields
    district_name = fields.Char(string='District / जिला', related='notification_id.district_id.name', store=True)
    tehsil_name = fields.Char(string='Tehsil / तहसील', related='notification_id.tehsil_id.name', store=True)
    village_name = fields.Char(string='Village / ग्राम', related='notification_id.village_id.name', store=True)
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन', related='notification_id.public_purpose', store=True)
