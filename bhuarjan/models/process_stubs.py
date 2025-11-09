# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid


# Stub models for Process menu items - to be implemented later
# These are minimal models to allow the module to load

class Section4Notification(models.Model):
    _name = 'bhu.section4.notification'
    _description = 'Section 4 Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Notification Name / अधिसूचना का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=False, tracking=True, 
                                  default=lambda self: self._default_project_id())
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True, tracking=True)
    
    # Computed field to show surveys for selected villages
    survey_ids = fields.Many2many('bhu.survey', compute='_compute_survey_ids', string='Surveys', readonly=True)
    survey_count = fields.Integer(string='Survey Count', compute='_compute_survey_ids', readonly=True)
    approved_survey_count = fields.Integer(string='Approved Survey Count', compute='_compute_survey_ids', readonly=True)
    all_surveys_approved = fields.Boolean(string='All Surveys Approved', compute='_compute_survey_ids', readonly=True)
    
    # Check if Section 11 exists for any of the villages (makes form read-only)
    has_section11 = fields.Boolean(string='Has Section 11', compute='_compute_has_section11', readonly=True)
    
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन का विवरण', 
                                 help='Description of public purpose for land acquisition', tracking=True)
    
    # Public Hearing Details
    public_hearing_date = fields.Date(string='Public Hearing Date / जन सुनवाई दिनांक', tracking=True)
    public_hearing_time = fields.Char(string='Public Hearing Time / जन सुनवाई समय', 
                                      help='e.g., 10:00 AM', tracking=True)
    public_hearing_place = fields.Char(string='Public Hearing Place / जन सुनवाई स्थान', tracking=True)
    
    # 11 Questions from the template
    q1_brief_description = fields.Text(string='(एक) लोक प्रयोजन का संक्षिप्त विवरण / Brief description of public purpose', tracking=True)
    q2_directly_affected = fields.Char(string='(दो) प्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of directly affected families', tracking=True)
    q3_indirectly_affected = fields.Char(string='(तीन) अप्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of indirectly affected families', tracking=True)
    q4_private_assets = fields.Char(string='(चार) प्रभावित क्षेत्र में निजी मकानों तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of private houses and other assets', tracking=True)
    q5_government_assets = fields.Char(string='(पाँच) प्रभावित क्षेत्र में शासकीय मकान तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of government houses and other assets', tracking=True)
    q6_minimal_acquisition = fields.Char(string='(छः) क्या प्रस्तावित अर्जन न्यूनतम है? / Is the proposed acquisition minimal?', tracking=True)
    q7_alternatives_considered = fields.Text(string='(सात) क्या संभव विकल्पों और इसकी साध्यता पर विचार कर लिया गया है? / Have possible alternatives and their feasibility been considered?', tracking=True)
    q8_total_cost = fields.Char(string='(आठ) परियोजना की कुल लागत / Total cost of the project', tracking=True)
    q9_project_benefits = fields.Text(string='(नौ) परियोजना से होने वाला लाभ / Benefits from the project', tracking=True)
    q10_compensation_measures = fields.Text(string='(दस) प्रस्तावित सामाजिक समाघात की प्रतिपूर्ति के लिये उपाय तथा उस पर होने वाला संभावित व्यय / Measures for compensation and likely expenditure', tracking=True)
    q11_other_components = fields.Text(string='(ग्यारह) परियोजना द्वारा प्रभावित होने वाले अन्य घटक / Other components affected by the project', tracking=True)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Notification / हस्ताक्षरित अधिसूचना')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है', compute='_compute_has_signed_document', store=True)
    
    # Collector signature
    collector_signature = fields.Binary(string='Collector Signature / कलेक्टर हस्ताक्षर')
    collector_signature_filename = fields.Char(string='Signature File Name')
    collector_name = fields.Char(string='Collector Name / कलेक्टर का नाम', tracking=True)
    
    # UUID for QR code
    notification_uuid = fields.Char(string='Notification UUID', copy=False, readonly=True, index=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
        ('signed', 'Signed / हस्ताक्षरित'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
    
    @api.depends('project_id', 'village_ids')
    def _compute_survey_ids(self):
        """Compute surveys for selected villages and project"""
        for record in self:
            if record.project_id and record.village_ids:
                surveys = self.env['bhu.survey'].search([
                    ('project_id', '=', record.project_id.id),
                    ('village_id', 'in', record.village_ids.ids)
                ])
                record.survey_ids = [(6, 0, surveys.ids)]
                record.survey_count = len(surveys)
                # Treat both 'approved' and 'locked' as approved
                approved_or_locked_surveys = surveys.filtered(lambda s: s.state in ('approved', 'locked'))
                record.approved_survey_count = len(approved_or_locked_surveys)
                # Check if all surveys are approved or locked (and there are surveys)
                record.all_surveys_approved = len(surveys) > 0 and len(approved_or_locked_surveys) == len(surveys)
            else:
                record.survey_ids = [(5, 0, 0)]
                record.survey_count = 0
                record.approved_survey_count = 0
                record.all_surveys_approved = False
    
    @api.depends('project_id', 'village_ids')
    def _compute_has_section11(self):
        """Check if Section 11 Preliminary Report exists for any of the villages"""
        for record in self:
            if record.project_id and record.village_ids:
                section11_reports = self.env['bhu.section11.preliminary.report'].search([
                    ('project_id', '=', record.project_id.id),
                    ('village_id', 'in', record.village_ids.ids)
                ], limit=1)
                record.has_section11 = bool(section11_reports)
            else:
                record.has_section11 = False
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists, otherwise use first available project"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        # Fallback to first available project if PROJ01 doesn't exist
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section4.notification') or 'New'
            if not vals.get('notification_uuid'):
                vals['notification_uuid'] = str(uuid.uuid4())
            # Set default project_id if not provided - always set it to avoid NOT NULL constraint violation
            if not vals.get('project_id'):
                project_id = self._default_project_id()
                if project_id:
                    vals['project_id'] = project_id
                else:
                    # If no project exists at all, we can't create the record
                    # This should not happen if sample_project_data.xml is loaded first
                    # But if it does, the post-init hook will fix it
                    # For now, we'll try to use any project as a last resort
                    any_project = self.env['bhu.project'].search([], limit=1)
                    if any_project:
                        vals['project_id'] = any_project.id
        return super().create(vals_list)
    
    def _get_consolidated_village_data(self):
        """Get consolidated survey data grouped by village"""
        self.ensure_one()
        
        # Get all approved or locked surveys for selected villages in the project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', 'in', self.village_ids.ids),
            ('state', 'in', ('approved', 'locked'))
        ])
        
        # Group surveys by village and calculate totals
        village_data = {}
        for survey in surveys:
            village = survey.village_id
            if village.id not in village_data:
                # Get district and tehsil from village or survey
                district_name = village.district_id.name if village.district_id else (survey.district_name or 'Raigarh (Chhattisgarh)')
                tehsil_name = village.tehsil_id.name if village.tehsil_id else (survey.tehsil_id.name or '')
                
                village_data[village.id] = {
                    'village_id': village.id,
                    'village_name': village.name,
                    'district': district_name,
                    'tehsil': tehsil_name,
                    'total_area': 0.0,
                    'surveys': []
                }
            # Sum up acquired area for all khasras in this village
            village_data[village.id]['total_area'] += survey.acquired_area or 0.0
            village_data[village.id]['surveys'].append(survey.id)
        
        # Convert to list sorted by village name
        consolidated_list = []
        for village_id in sorted(village_data.keys(), key=lambda x: village_data[x]['village_name']):
            consolidated_list.append(village_data[village_id])
        
        return consolidated_list
    
    def get_formatted_hearing_date(self):
        """Format public hearing date for display"""
        self.ensure_one()
        if self.public_hearing_date:
            return self.public_hearing_date.strftime('%d/%m/%Y')
        return '........................'
    
    def get_qr_code_data(self):
        """Generate QR code data for the notification"""
        try:
            import qrcode
            import io
            import base64
            
            # Ensure UUID exists
            if not self.notification_uuid:
                self.write({'notification_uuid': str(uuid.uuid4())})
            
            # Generate QR code URL - using notification UUID
            qr_url = f"https://bhuarjan.com/bhuarjan/section4/{self.notification_uuid}/download"
            
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
        except Exception as e:
            return None
    
    def action_generate_pdf(self):
        """Generate Section 4 Notification PDF"""
        self.ensure_one()
        
        # Validate that all surveys for selected villages are approved
        if not self.project_id or not self.village_ids:
            raise ValidationError(_('Please select a project and at least one village.'))
        
        # Get all surveys for selected villages
        all_surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', 'in', self.village_ids.ids)
        ])
        
        if not all_surveys:
            raise ValidationError(_('No surveys found for the selected villages. Please create surveys first.'))
        
        # Check if all surveys are approved or locked (treat locked as approved)
        non_approved_surveys = all_surveys.filtered(lambda s: s.state not in ('approved', 'locked'))
        if non_approved_surveys:
            village_names = ', '.join(set(non_approved_surveys.mapped('village_id.name')))
            raise ValidationError(_(
                'Cannot generate Section 4 Notification. Some surveys are not approved yet.\n\n'
                'Villages with non-approved surveys: %s\n'
                'Please approve all surveys before generating the notification.'
            ) % village_names)
        
        self.state = 'generated'
        
        # Lock all approved surveys for the selected villages (skip already locked ones)
        approved_surveys = all_surveys.filtered(lambda s: s.state == 'approved')
        if approved_surveys:
            approved_surveys.write({'state': 'locked'})
            self.message_post(
                body=_('Locked %d survey(s) for villages: %s') % (
                    len(approved_surveys),
                    ', '.join(self.village_ids.mapped('name'))
                )
            )
        
        # Use wizard to generate PDF (reuse existing logic)
        # Always create a fresh wizard with current data to ensure report has all data
        wizard = self.env['bhu.section4.notification.wizard'].create({
            'project_id': self.project_id.id,
            'village_ids': [(6, 0, self.village_ids.ids)],
            'public_purpose': self.public_purpose,
            'public_hearing_date': self.public_hearing_date,
            'public_hearing_time': self.public_hearing_time,
            'public_hearing_place': self.public_hearing_place,
            'q1_brief_description': self.q1_brief_description,
            'q2_directly_affected': self.q2_directly_affected,
            'q3_indirectly_affected': self.q3_indirectly_affected,
            'q4_private_assets': self.q4_private_assets,
            'q5_government_assets': self.q5_government_assets,
            'q6_minimal_acquisition': self.q6_minimal_acquisition,
            'q7_alternatives_considered': self.q7_alternatives_considered,
            'q8_total_cost': self.q8_total_cost,
            'q9_project_benefits': self.q9_project_benefits,
            'q10_compensation_measures': self.q10_compensation_measures,
            'q11_other_components': self.q11_other_components,
        })
        
        report_action = self.env.ref('bhuarjan.action_report_section4_notification')
        return report_action.report_action(wizard)
    
    def action_mark_signed(self):
        """Mark notification as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()


class Section4NotificationWizard(models.TransientModel):
    _name = 'bhu.section4.notification.wizard'
    _description = 'Section 4 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True)
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन का विवरण', 
                                 help='Description of public purpose for land acquisition')
    
    # Public Hearing Details
    public_hearing_date = fields.Date(string='Public Hearing Date / जन सुनवाई दिनांक')
    public_hearing_time = fields.Char(string='Public Hearing Time / जन सुनवाई समय', 
                                      help='e.g., 10:00 AM')
    public_hearing_place = fields.Char(string='Public Hearing Place / जन सुनवाई स्थान')
    
    # 11 Questions from the template
    q1_brief_description = fields.Text(string='(एक) लोक प्रयोजन का संक्षिप्त विवरण / Brief description of public purpose')
    q2_directly_affected = fields.Char(string='(दो) प्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of directly affected families')
    q3_indirectly_affected = fields.Char(string='(तीन) अप्रत्यक्ष रूप से प्रभावित परिवारों की संख्या / Number of indirectly affected families')
    q4_private_assets = fields.Char(string='(चार) प्रभावित क्षेत्र में निजी मकानों तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of private houses and other assets')
    q5_government_assets = fields.Char(string='(पाँच) प्रभावित क्षेत्र में शासकीय मकान तथा अन्य परिसंपत्तियों की अनुमानित संख्या / Estimated number of government houses and other assets')
    q6_minimal_acquisition = fields.Char(string='(छः) क्या प्रस्तावित अर्जन न्यूनतम है? / Is the proposed acquisition minimal?')
    q7_alternatives_considered = fields.Text(string='(सात) क्या संभव विकल्पों और इसकी साध्यता पर विचार कर लिया गया है? / Have possible alternatives and their feasibility been considered?')
    q8_total_cost = fields.Char(string='(आठ) परियोजना की कुल लागत / Total cost of the project')
    q9_project_benefits = fields.Text(string='(नौ) परियोजना से होने वाला लाभ / Benefits from the project')
    q10_compensation_measures = fields.Text(string='(दस) प्रस्तावित सामाजिक समाघात की प्रतिपूर्ति के लिये उपाय तथा उस पर होने वाला संभावित व्यय / Measures for compensation and likely expenditure')
    q11_other_components = fields.Text(string='(ग्यारह) परियोजना द्वारा प्रभावित होने वाले अन्य घटक / Other components affected by the project')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset villages when project changes and set domain"""
        self.village_ids = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_ids': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_ids': []}}

    def _get_consolidated_village_data(self):
        """Get consolidated survey data grouped by village"""
        self.ensure_one()
        
        # Get all approved or locked surveys for selected villages in the project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', 'in', self.village_ids.ids),
            ('state', 'in', ('approved', 'locked'))
        ])
        
        # Group surveys by village and calculate totals
        village_data = {}
        for survey in surveys:
            village = survey.village_id
            if village.id not in village_data:
                # Get district and tehsil from village or survey
                district_name = village.district_id.name if village.district_id else (survey.district_name or 'Raigarh (Chhattisgarh)')
                tehsil_name = village.tehsil_id.name if village.tehsil_id else (survey.tehsil_id.name or '')
                
                village_data[village.id] = {
                    'village_id': village.id,
                    'village_name': village.name,
                    'district': district_name,
                    'tehsil': tehsil_name,
                    'total_area': 0.0,
                    'surveys': []
                }
            # Sum up acquired area for all khasras in this village
            village_data[village.id]['total_area'] += survey.acquired_area or 0.0
            village_data[village.id]['surveys'].append(survey.id)
        
        # Convert to list sorted by village name
        consolidated_list = []
        for village_id in sorted(village_data.keys(), key=lambda x: village_data[x]['village_name']):
            consolidated_list.append(village_data[village_id])
        
        return consolidated_list

    def get_formatted_hearing_date(self):
        """Format public hearing date for display"""
        self.ensure_one()
        if self.public_hearing_date:
            return self.public_hearing_date.strftime('%d/%m/%Y')
        return '........................'
    
    def action_generate_pdf(self):
        """Generate Section 4 Notification PDF and create notification record"""
        self.ensure_one()
        
        if not self.village_ids:
            raise ValidationError(_('Please select at least one village.'))
        
        # Get consolidated data
        consolidated_data = self._get_consolidated_village_data()
        
        if not consolidated_data:
            raise ValidationError(_('No approved surveys found for the selected villages.'))
        
        # Create notification record
        notification = self.env['bhu.section4.notification'].create({
            'project_id': self.project_id.id,
            'village_ids': [(6, 0, self.village_ids.ids)],
            'public_purpose': self.public_purpose,
            'public_hearing_date': self.public_hearing_date,
            'public_hearing_time': self.public_hearing_time,
            'public_hearing_place': self.public_hearing_place,
            'q1_brief_description': self.q1_brief_description,
            'q2_directly_affected': self.q2_directly_affected,
            'q3_indirectly_affected': self.q3_indirectly_affected,
            'q4_private_assets': self.q4_private_assets,
            'q5_government_assets': self.q5_government_assets,
            'q6_minimal_acquisition': self.q6_minimal_acquisition,
            'q7_alternatives_considered': self.q7_alternatives_considered,
            'q8_total_cost': self.q8_total_cost,
            'q9_project_benefits': self.q9_project_benefits,
            'q10_compensation_measures': self.q10_compensation_measures,
            'q11_other_components': self.q11_other_components,
            'state': 'generated',
        })
        
        # Generate PDF report - pass the wizard recordset
        report_action = self.env.ref('bhuarjan.action_report_section4_notification')
        return report_action.report_action(self)


class ExpertCommitteeReport(models.Model):
    _name = 'bhu.expert.committee.report'
    _description = 'Expert Committee Report / विशेषज्ञ समिति रिपोर्ट'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Report Name / रिपोर्ट का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True,
                                  default=lambda self: self._default_project_id(), tracking=True)
    
    _sql_constraints = [
        ('project_unique', 'UNIQUE(project_id)', 'Only one Expert Committee Report is allowed per project.')
    ]
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists, otherwise use first available project"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        # Fallback to first available project if PROJ01 doesn't exist
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    # Original report file (unsigned)
    report_file = fields.Binary(string='Report File / रिपोर्ट फ़ाइल')
    report_filename = fields.Char(string='File Name / फ़ाइल नाम')
    
    # Signed document fields (similar to Section 4 Notification)
    signed_document_file = fields.Binary(string='Signed Report / हस्ताक्षरित रिपोर्ट')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है', 
                                         compute='_compute_has_signed_document', store=True)
    
    # Signatory information
    signatory_name = fields.Char(string='Signatory Name / हस्ताक्षरकर्ता का नाम', tracking=True)
    signatory_designation = fields.Char(string='Signatory Designation / हस्ताक्षरकर्ता का पद', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('submitted', 'Submitted / प्रस्तुत'),
        ('approved', 'Approved / स्वीकृत'),
        ('rejected', 'Rejected / अस्वीकृत'),
        ('signed', 'Signed / हस्ताक्षरित'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.expert.committee.report') or 'New'
            # Set default project_id if not provided
            if not vals.get('project_id'):
                project_id = self._default_project_id()
                if project_id:
                    vals['project_id'] = project_id
                else:
                    # If no project exists at all, we can't create the record
                    # This should not happen if sample_project_data.xml is loaded first
                    # But if it does, the post-init hook will fix it
                    # For now, we'll try to use any project as a last resort
                    any_project = self.env['bhu.project'].search([], limit=1)
                    if any_project:
                        vals['project_id'] = any_project.id
        return super().create(vals_list)
    
    def action_mark_signed(self):
        """Mark report as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()
    
    def action_approve(self):
        """Approve the Expert Committee Report"""
        self.ensure_one()
        if self.state not in ['draft', 'submitted']:
            raise ValidationError(_('Only draft or submitted reports can be approved.'))
        self.state = 'approved'
        return True
    
    def action_reject(self):
        """Reject the Expert Committee Report"""
        self.ensure_one()
        if self.state not in ['draft', 'submitted']:
            raise ValidationError(_('Only draft or submitted reports can be rejected.'))
        self.state = 'rejected'
        return True
    
    def action_submit(self):
        """Submit the Expert Committee Report for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Only draft reports can be submitted.'))
        self.state = 'submitted'
        return True
    
    def action_generate_order(self):
        """Generate Expert Committee Order - Opens wizard with current report's project"""
        self.ensure_one()
        return {
            'name': _('Generate Expert Committee Order / विशेषज्ञ समिति आदेश जेनरेट करें'),
            'type': 'ir.actions.act_window',
            'res_model': 'bhu.expert.committee.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
            }
        }


class ExpertCommitteeOrderWizard(models.TransientModel):
    _name = 'bhu.expert.committee.order.wizard'
    _description = 'Expert Committee Order Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)

    def action_generate_order(self):
        """Generate Order - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Order generation will be implemented soon.'),
                'type': 'info',
            }
        }


class Section11PreliminaryReport(models.Model):
    _name = 'bhu.section11.preliminary.report'
    _description = 'Section 11 Preliminary Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Report Name', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project', required=True, tracking=True,
                                  default=lambda self: self._default_project_id())
    village_id = fields.Many2one('bhu.village', string='Village', required=True, tracking=True)
    district_id = fields.Many2one('bhu.district', string='District', related='village_id.district_id', 
                                   store=True, readonly=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', related='village_id.tehsil_id', 
                                store=True, readonly=True)
    
    # Notification Details
    notification_number = fields.Char(string='Notification Number', tracking=True)
    publication_date = fields.Date(string='Publication Date', tracking=True)
    
    # Schedule/Table - Land Parcels (One2many)
    land_parcel_ids = fields.One2many('bhu.section11.land.parcel', 'report_id', 
                                      string='Land Parcels', tracking=True)
    
    # Computed fields for list view
    khasra_numbers = fields.Char(string='Khasra Numbers', compute='_compute_khasra_info', store=False)
    khasra_count = fields.Integer(string='Khasra Count', compute='_compute_khasra_info', store=False)
    survey_numbers = fields.Char(string='Survey Numbers', compute='_compute_survey_info', store=False)
    survey_date = fields.Date(string='Survey Date', compute='_compute_survey_info', store=False)
    
    @api.depends('land_parcel_ids.khasra_number')
    def _compute_khasra_info(self):
        """Compute khasra numbers and count for list view"""
        for record in self:
            if record.land_parcel_ids:
                khasras = record.land_parcel_ids.mapped('khasra_number')
                record.khasra_numbers = ', '.join([k for k in khasras if k])
                record.khasra_count = len([k for k in khasras if k])
            else:
                record.khasra_numbers = ''
                record.khasra_count = 0
    
    @api.depends('village_id', 'project_id')
    def _compute_survey_info(self):
        """Compute survey numbers and date from related surveys"""
        for record in self:
            if record.village_id and record.project_id:
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('project_id', '=', record.project_id.id),
                    ('state', '=', 'locked')
                ], order='survey_date desc', limit=10)
                if surveys:
                    survey_names = surveys.mapped('name')
                    record.survey_numbers = ', '.join([s for s in survey_names if s])
                    record.survey_date = surveys[0].survey_date if surveys[0].survey_date else False
                else:
                    record.survey_numbers = ''
                    record.survey_date = False
            else:
                record.survey_numbers = ''
                record.survey_date = False
    
    # Paragraph 2: Claims/Objections Information
    paragraph_2_claims_info = fields.Text(string='Paragraph 2: Claims/Objections Info',
                                          help='Information about claims/objections submission (60 days deadline)',
                                          tracking=True)
    
    # Paragraph 3: Land Map Inspection
    paragraph_3_map_inspection_location = fields.Char(string='Map Inspection Location',
                                                       help='Location where land map can be inspected (SDO Revenue office)',
                                                       tracking=True)
    
    # Paragraph 4: Displacement
    paragraph_4_is_displacement = fields.Boolean(string='Is Displacement Involved?',
                                                 default=False, tracking=True)
    paragraph_4_affected_families_count = fields.Integer(string='Affected Families Count',
                                                         tracking=True)
    
    # Paragraph 5: Exemption or SIA Justification
    paragraph_5_is_exemption = fields.Boolean(string='Is Exemption Granted?',
                                               default=False, tracking=True)
    paragraph_5_exemption_details = fields.Text(string='Exemption Details',
                                                 help='Details of exemption notification (number, date, exempted chapters)',
                                                 tracking=True)
    paragraph_5_sia_justification = fields.Text(string='SIA Justification',
                                                help='SIA justification details (last resort, social benefits)',
                                                tracking=True)
    
    # Paragraph 6: Rehabilitation Administrator
    paragraph_6_rehab_admin_name = fields.Char(string='Rehabilitation Administrator',
                                               help='Name/Designation of Rehabilitation and Resettlement Administrator',
                                               tracking=True)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Report')
    signed_document_filename = fields.Char(string='Signed File Name')
    signed_date = fields.Date(string='Signed Date', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document', 
                                         compute='_compute_has_signed_document', store=True)
    
    # Collector signature
    collector_signature = fields.Binary(string='Collector Signature')
    collector_signature_filename = fields.Char(string='Signature File Name')
    collector_name = fields.Char(string='Collector Name', tracking=True)
    
    # UUID for QR code
    report_uuid = fields.Char(string='Report UUID', copy=False, readonly=True, index=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('signed', 'Signed'),
    ], string='Status', default='draft', tracking=True)
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
            # Auto-sign when signed document is uploaded
            if record.has_signed_document and record.state != 'signed':
                record.state = 'signed'
                if not record.signed_date:
                    record.signed_date = fields.Date.today()
    
    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Auto-populate land parcels from locked surveys when village is selected"""
        self._populate_land_parcels_from_surveys()
    
    def _populate_land_parcels_from_surveys(self):
        """Helper method to populate land parcels from locked surveys"""
        self.ensure_one()
        if not self.village_id or not self.project_id:
            return
        
        # Search for locked surveys for the selected village and project
        locked_surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('project_id', '=', self.project_id.id),
            ('state', '=', 'locked')
        ], order='khasra_number')
        
        # Clear existing land parcels
        self.land_parcel_ids = [(5, 0, 0)]
        
        # Create land parcel records from locked surveys
        parcel_vals = []
        for survey in locked_surveys:
            # Get department name for authorized officer if available
            authorized_officer = ''
            if survey.department_id:
                authorized_officer = survey.department_id.name or ''
            
            # Get public purpose from project if available
            public_purpose = ''
            if self.project_id:
                public_purpose = self.project_id.name or ''
            
            parcel_vals.append((0, 0, {
                'khasra_number': survey.khasra_number or '',
                'area_in_hectares': survey.acquired_area or 0.0,
                'authorized_officer': authorized_officer,
                'public_purpose_description': public_purpose,
            }))
        
        # Set the land parcels
        if parcel_vals:
            self.land_parcel_ids = parcel_vals
        
        # Auto-populate compensation lines
        self._populate_compensation_lines()
    
    def _populate_compensation_lines(self):
        """Helper method to populate compensation lines from land parcels and surveys"""
        self.ensure_one()
        if not self.land_parcel_ids:
            return
        
        # Clear existing compensation lines
        self.compensation_line_ids = [(5, 0, 0)]
        
        # Get all surveys for the khasras in land parcels
        khasra_numbers = self.land_parcel_ids.mapped('khasra_number')
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('project_id', '=', self.project_id.id),
            ('khasra_number', 'in', khasra_numbers),
            ('state', '=', 'locked')
        ])
        
        # Create compensation line for each survey
        line_vals = []
        serial = 1
        for survey in surveys:
            # Get land parcel for this khasra
            parcel = self.land_parcel_ids.filtered(lambda p: p.khasra_number == survey.khasra_number)
            if not parcel:
                continue
            
            # Create a line for each landowner
            for landowner in survey.landowner_ids:
                # Determine land type
                is_irrigated = survey.irrigation_type == 'irrigated'
                is_unirrigated = survey.irrigation_type == 'unirrigated'
                
                line_vals.append((0, 0, {
                    'serial_number': serial,
                    'landowner_id': landowner.id,
                    'khasra_number': survey.khasra_number or '',
                    'acquired_area': parcel[0].area_hectares or 0.0,
                    'is_irrigated': is_irrigated,
                    'is_unirrigated': is_unirrigated,
                    'is_fallow': False,  # Default, can be updated manually
                    'total_held_khasra': survey.khasra_number or '',
                    'total_held_area': survey.total_area or 0.0,
                    'acquired_revenue': 0.0,  # Can be updated manually
                }))
                serial += 1
        
        # Set the compensation lines
        if line_vals:
            self.compensation_line_ids = line_vals
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists, otherwise use first available project"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        # Fallback to first available project if PROJ01 doesn't exist
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            # Generate UUID if not provided
            if not vals.get('report_uuid'):
                vals['report_uuid'] = str(uuid.uuid4())
        records = super().create(vals_list)
        # Auto-populate land parcels after creation if village and project are set
        for record in records:
            if record.village_id and record.project_id:
                record._populate_land_parcels_from_surveys()
        return records
    
    def get_qr_code_data(self):
        """Generate QR code data for the report"""
        try:
            import qrcode
            import io
            import base64
            
            # Ensure UUID exists
            if not self.report_uuid:
                self.write({'report_uuid': str(uuid.uuid4())})
            
            # Generate QR code URL - using report UUID
            qr_url = f"https://bhuarjan.com/bhuarjan/section11/{self.report_uuid}/download"
            
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
        except Exception as e:
            return None
    
    def action_generate_pdf(self):
        """Generate Section 11 Preliminary Report PDF"""
        self.ensure_one()
        self.state = 'generated'
        return self.env.ref('bhuarjan.action_report_section11_preliminary').report_action(self)
    
    @api.model
    def action_open_wizard(self):
        """Open wizard to generate new report - works without record selection"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Section 11 Preliminary Report',
            'res_model': 'bhu.section11.preliminary.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    


class Section11LandParcel(models.Model):
    _name = 'bhu.section11.land.parcel'
    _description = 'Section 11 Land Parcel'
    _order = 'khasra_number'

    report_id = fields.Many2one('bhu.section11.preliminary.report', string='Report', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number', required=True)
    area_in_hectares = fields.Float(string='Area (Hectares)', required=True, digits=(16, 4))
    authorized_officer = fields.Char(string='Authorized Officer',
                                     help='Officer authorized by Section 12')
    public_purpose_description = fields.Text(string='Public Purpose Description')
    
    # Related fields from report
    district_id = fields.Many2one('bhu.district', string='District', related='report_id.district_id', store=True, readonly=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', related='report_id.tehsil_id', store=True, readonly=True)
    village_id = fields.Many2one('bhu.village', string='Village', related='report_id.village_id', store=True, readonly=True)
    project_id = fields.Many2one('bhu.project', string='Project', related='report_id.project_id', store=True, readonly=True)
    
    # Computed fields from related survey
    survey_number = fields.Char(string='Survey Number', compute='_compute_survey_info', store=False)
    survey_date = fields.Date(string='Survey Date', compute='_compute_survey_info', store=False)
    
    @api.depends('khasra_number', 'report_id.village_id', 'report_id.project_id')
    def _compute_survey_info(self):
        """Compute survey number and date from related survey"""
        for record in self:
            if record.khasra_number and record.report_id and record.report_id.village_id and record.report_id.project_id:
                survey = self.env['bhu.survey'].search([
                    ('khasra_number', '=', record.khasra_number),
                    ('village_id', '=', record.report_id.village_id.id),
                    ('project_id', '=', record.report_id.project_id.id),
                    ('state', '=', 'locked')
                ], limit=1)
                if survey:
                    record.survey_number = survey.name or ''
                    record.survey_date = survey.survey_date or False
                else:
                    record.survey_number = ''
                    record.survey_date = False
            else:
                record.survey_number = ''
                record.survey_date = False


class Section19Notification(models.Model):
    _name = 'bhu.section19.notification'
    _description = 'Section 19 Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Notification Name / अधिसूचना का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=False, tracking=True,
                                  default=lambda self: self._default_project_id())
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True, tracking=True)
    
    # Notification Details
    notification_number = fields.Char(string='Notification Number / अधिसूचना संख्या', tracking=True,
                                      help='e.g., /अ-82/2015-16')
    notification_date = fields.Date(string='Notification Date / अधिसूचना दिनांक', default=fields.Date.today, tracking=True)
    
    # District, Tehsil - computed from villages
    district_id = fields.Many2one('bhu.district', string='District / जिला', compute='_compute_location', store=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', compute='_compute_location', store=True)
    
    # Public Purpose
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन', 
                                 help='Description of public purpose for land acquisition', tracking=True)
    
    # Schedule/Table - Land Parcels (One2many)
    land_parcel_ids = fields.One2many('bhu.section19.land.parcel', 'notification_id', 
                                      string='Land Parcels / भूमि खंड', tracking=True)
    
    # Computed total land area
    total_land_area = fields.Float(string='Total Land Area (Hectares) / कुल भूमि क्षेत्रफल (हेक्टेयर)',
                                   compute='_compute_total_land_area', store=True, digits=(16, 4))
    
    # Computed fields for list view
    khasra_numbers = fields.Char(string='Khasra Numbers / खसरा नंबर', compute='_compute_khasra_info', store=False)
    khasra_count = fields.Integer(string='Khasra Count / खसरा संख्या', compute='_compute_khasra_info', store=False)
    
    # Paragraph 2: Map Inspection
    sdo_revenue_name = fields.Char(string='SDO (Revenue) Name / अनुविभागीय अधिकारी (राजस्व) का नाम',
                                   tracking=True)
    sdo_office_location = fields.Char(string='SDO Office Location / अनुविभागीय अधिकारी कार्यालय स्थान',
                                      tracking=True)
    
    # Paragraph 3: Displacement and Rehabilitation
    is_displacement_involved = fields.Boolean(string='Is Displacement Involved? / क्या विस्थापन शामिल है?',
                                              default=False, tracking=True)
    
    # Rehabilitation land details (conditional)
    rehab_village_id = fields.Many2one('bhu.village', string='Rehabilitation Village / पुनर्वास ग्राम',
                                       tracking=True)
    rehab_tehsil_id = fields.Many2one('bhu.tehsil', string='Rehabilitation Tehsil / पुनर्वास तहसील',
                                      tracking=True)
    rehab_district_id = fields.Many2one('bhu.district', string='Rehabilitation District / पुनर्वास जिला',
                                        tracking=True)
    rehab_khasra_number = fields.Char(string='Rehabilitation Khasra Number / पुनर्वास खसरा नंबर',
                                      tracking=True)
    rehab_area_hectares = fields.Float(string='Rehabilitation Area (Hectares) / पुनर्वास क्षेत्रफल (हेक्टेयर)',
                                        digits=(16, 4), tracking=True)
    rehab_officer_name = fields.Char(string='Rehabilitation Officer / पुनर्वास अधिकारी',
                                     tracking=True)
    rehab_officer_office_location = fields.Char(string='Rehabilitation Officer Office / पुनर्वास अधिकारी कार्यालय',
                                                 tracking=True)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Notification / हस्ताक्षरित अधिसूचना')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है', 
                                         compute='_compute_has_signed_document', store=True)
    
    # Collector signature
    collector_signature = fields.Binary(string='Collector Signature / कलेक्टर हस्ताक्षर')
    collector_signature_filename = fields.Char(string='Signature File Name')
    collector_name = fields.Char(string='Collector Name / कलेक्टर का नाम', tracking=True)
    
    # UUID for QR code
    notification_uuid = fields.Char(string='Notification UUID', copy=False, readonly=True, index=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
        ('signed', 'Signed / हस्ताक्षरित'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
            # Auto-sign when signed document is uploaded
            if record.has_signed_document and record.state != 'signed':
                record.state = 'signed'
                if not record.signed_date:
                    record.signed_date = fields.Date.today()
    
    @api.depends('village_ids')
    def _compute_location(self):
        """Compute district and tehsil from villages"""
        for record in self:
            if record.village_ids:
                # Use first village's district and tehsil (assuming all villages are in same district/tehsil)
                first_village = record.village_ids[0]
                record.district_id = first_village.district_id.id if first_village.district_id else False
                record.tehsil_id = first_village.tehsil_id.id if first_village.tehsil_id else False
            else:
                record.district_id = False
                record.tehsil_id = False
    
    @api.depends('land_parcel_ids.area_hectares')
    def _compute_total_land_area(self):
        """Compute total land area from land parcels"""
        for record in self:
            record.total_land_area = sum(record.land_parcel_ids.mapped('area_hectares'))
    
    @api.depends('land_parcel_ids.khasra_number')
    def _compute_khasra_info(self):
        """Compute khasra numbers and count for list view"""
        for record in self:
            if record.land_parcel_ids:
                khasras = record.land_parcel_ids.mapped('khasra_number')
                record.khasra_numbers = ', '.join([k for k in khasras if k])
                record.khasra_count = len([k for k in khasras if k])
            else:
                record.khasra_numbers = ''
                record.khasra_count = 0
    
    @api.onchange('village_ids', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Auto-populate land parcels from Section 11 approved khasras (excluding objections) when villages are selected"""
        self._populate_land_parcels_from_surveys()
    
    def _populate_land_parcels_from_surveys(self):
        """Helper method to populate land parcels from Section 11 approved khasras, excluding those with objections"""
        self.ensure_one()
        if not self.village_ids or not self.project_id:
            return
        
        # Get all Section 11 Preliminary Reports for selected villages and project (approved/generated)
        section11_reports = self.env['bhu.section11.preliminary.report'].search([
            ('village_id', 'in', self.village_ids.ids),
            ('project_id', '=', self.project_id.id),
            ('state', 'in', ['generated', 'signed'])
        ])
        
        # Get all khasra numbers from Section 11 land parcels
        section11_khasras = set()
        khasra_area_map = {}
        for report in section11_reports:
            for parcel in report.land_parcel_ids:
                if parcel.khasra_number:
                    section11_khasras.add(parcel.khasra_number)
                    # Store area (use the latest one if duplicate khasras exist)
                    khasra_area_map[parcel.khasra_number] = parcel.area_in_hectares
        
        # Get all khasra numbers that have objections (Section 15)
        objections = self.env['bhu.section15.objection'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', 'in', self.village_ids.ids),
            ('status', '!=', 'resolved')  # Exclude resolved objections
        ])
        
        objection_khasras = set()
        for objection in objections:
            if objection.survey_id and objection.survey_id.khasra_number:
                objection_khasras.add(objection.survey_id.khasra_number)
        
        # Filter out khasras with objections
        approved_khasras = section11_khasras - objection_khasras
        
        # Clear existing land parcels
        self.land_parcel_ids = [(5, 0, 0)]
        
        # Create land parcel records from approved khasras
        parcel_vals = []
        for khasra_number in sorted(approved_khasras):
            parcel_vals.append((0, 0, {
                'khasra_number': khasra_number,
                'area_hectares': khasra_area_map.get(khasra_number, 0.0),
            }))
        
        # Set the land parcels
        if parcel_vals:
            self.land_parcel_ids = parcel_vals
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists, otherwise use first available project"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section19.notification') or 'New'
            # Generate UUID if not provided
            if not vals.get('notification_uuid'):
                vals['notification_uuid'] = str(uuid.uuid4())
            # Set default project_id if not provided
            if not vals.get('project_id'):
                project_id = self._default_project_id()
                if project_id:
                    vals['project_id'] = project_id
        records = super().create(vals_list)
        # Auto-populate land parcels after creation if villages and project are set
        for record in records:
            if record.village_ids and record.project_id:
                record._populate_land_parcels_from_surveys()
        return records
    
    def get_qr_code_data(self):
        """Generate QR code data for the notification"""
        try:
            import qrcode
            import io
            import base64
            
            # Ensure UUID exists
            if not self.notification_uuid:
                self.write({'notification_uuid': str(uuid.uuid4())})
            
            # Generate QR code URL - using notification UUID
            qr_url = f"https://bhuarjan.com/bhuarjan/section19/{self.notification_uuid}/download"
            
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
        except Exception as e:
            return None
    
    def action_generate_pdf(self):
        """Generate Section 19 Notification PDF"""
        self.ensure_one()
        self.state = 'generated'
        return self.env.ref('bhuarjan.action_report_section19_notification').report_action(self)
    
    def action_mark_signed(self):
        """Mark notification as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()
    
    @api.model
    def action_open_wizard(self):
        """Open wizard to generate new notification - works without record selection"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Section 19 Notification',
            'res_model': 'bhu.section19.notification.wizard',
            'view_mode': 'form',
            'target': 'new',
        }


class Section19LandParcel(models.Model):
    _name = 'bhu.section19.land.parcel'
    _description = 'Section 19 Land Parcel'
    _order = 'khasra_number'

    notification_id = fields.Many2one('bhu.section19.notification', string='Notification', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True)
    area_hectares = fields.Float(string='Area (Hectares) / रकबा (हेक्टेयर में)', required=True, digits=(16, 4))


class Section19NotificationWizard(models.TransientModel):
    _name = 'bhu.section19.notification.wizard'
    _description = 'Section 19 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True)
    
    def action_generate_notification(self):
        """Create Section 19 Notification record and generate PDF"""
        self.ensure_one()
        
        # Create notification record
        notification = self.env['bhu.section19.notification'].create({
            'project_id': self.project_id.id,
            'village_ids': [(6, 0, self.village_ids.ids)],
            'state': 'generated',
        })
        
        # Generate PDF report
        report_action = self.env.ref('bhuarjan.action_report_section19_notification')
        return report_action.report_action(notification)


class Section11PreliminaryWizard(models.TransientModel):
    _name = 'bhu.section11.preliminary.wizard'
    _description = 'Section 11 Preliminary Report Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)

    def action_generate_report(self):
        """Create Section 11 Preliminary Report record"""
        self.ensure_one()
        
        # Create the report record
        report = self.env['bhu.section11.preliminary.report'].create({
            'project_id': self.project_id.id,
            'village_id': self.village_id.id,
        })
        
        # Open the form view
        return {
            'type': 'ir.actions.act_window',
            'name': _('Section 11 Preliminary Report'),
            'res_model': 'bhu.section11.preliminary.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }


class Section19NotificationWizard(models.TransientModel):
    _name = 'bhu.section19.notification.wizard'
    _description = 'Section 19 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_notification(self):
        """Generate Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notification generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DraftAward(models.Model):
    _name = 'bhu.draft.award'
    _description = 'Draft Award / अवार्ड आदेश'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Award Name / अवार्ड का नाम', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True,
                                 default=lambda self: self._default_project_id())
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # Case Details
    case_number = fields.Char(string='Case Number / भू.अर्जन प्र. क्र.', tracking=True,
                              help='e.g., 202301042100043/अ-82/2022-23')
    patwari_halka_number = fields.Char(string='Patwari Halka Number / प.ह.नं.', tracking=True,
                                       help='e.g., 38')
    
    # District, Tehsil - computed from village
    district_id = fields.Many2one('bhu.district', string='District / जिला', compute='_compute_location', store=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', compute='_compute_location', store=True)
    
    # Award Details
    award_number = fields.Char(string='Award Number / अवार्ड संख्या', tracking=True)
    award_date = fields.Date(string='Award Date / अवार्ड दिनांक', default=fields.Date.today, tracking=True)
    
    # Applicant (Executive Engineer)
    applicant_name = fields.Char(string='Applicant Name / आवेदक का नाम', tracking=True,
                                 default='कार्यपालन अभियंता, केलो परियोजना सर्वेक्षण संभाग, जिला- रायगढ़ (छ.ग.)')
    applicant_designation = fields.Char(string='Applicant Designation / आवेदक का पद', tracking=True)
    
    # Respondents (Landowners) - computed from Section 11
    respondent_ids = fields.Many2many('bhu.landowner', string='Respondents / अनावेदक', 
                                     compute='_compute_respondents', store=False)
    
    # Land Parcels (One2many) - populated from Section 11
    land_parcel_ids = fields.One2many('bhu.draft.award.land.parcel', 'award_id',
                                      string='Land Parcels / भूमि खंड', tracking=True)
    
    # Computed total land area
    total_land_area = fields.Float(string='Total Land Area (Hectares) / कुल भूमि क्षेत्रफल (हेक्टेयर)',
                                    compute='_compute_total_land_area', store=True, digits=(16, 4))
    total_khasra_count = fields.Integer(string='Total Khasra Count / कुल खसरा संख्या',
                                         compute='_compute_total_land_area', store=True)
    
    # Section 11 Reference
    section11_report_id = fields.Many2one('bhu.section11.preliminary.report', 
                                          string='Section 11 Report / धारा 11 रिपोर्ट',
                                          compute='_compute_section11_report', store=True)
    
    # Section 19 Reference
    section19_notification_id = fields.Many2one('bhu.section19.notification',
                                                 string='Section 19 Notification / धारा 19 अधिसूचना',
                                                 compute='_compute_section19_notification', store=True)
    
    # Publication Details
    section11_gazette_date = fields.Date(string='Section 11 Gazette Date / धारा 11 राजपत्र दिनांक', tracking=True)
    section11_gazette_part = fields.Char(string='Section 11 Gazette Part / धारा 11 राजपत्र भाग', tracking=True,
                                         help='e.g., Part-1')
    section11_gazette_page = fields.Char(string='Section 11 Gazette Page / धारा 11 राजपत्र पृष्ठ', tracking=True,
                                         help='e.g., Page No. 488')
    section11_newspaper_1_name = fields.Char(string='Newspaper 1 Name / समाचार पत्र 1 का नाम', tracking=True,
                                              help='e.g., नवभारत')
    section11_newspaper_1_date = fields.Date(string='Newspaper 1 Date / समाचार पत्र 1 दिनांक', tracking=True)
    section11_newspaper_2_name = fields.Char(string='Newspaper 2 Name / समाचार पत्र 2 का नाम', tracking=True,
                                              help='e.g., कांतिकारी संकेत')
    section11_newspaper_2_date = fields.Date(string='Newspaper 2 Date / समाचार पत्र 2 दिनांक', tracking=True)
    section11_munadi_date = fields.Date(string='Section 11 Munadi Date / धारा 11 मुनादी दिनांक', tracking=True)
    
    section19_gazette_date = fields.Date(string='Section 19 Gazette Date / धारा 19 राजपत्र दिनांक', tracking=True)
    section19_gazette_part = fields.Char(string='Section 19 Gazette Part / धारा 19 राजपत्र भाग', tracking=True)
    section19_gazette_page = fields.Char(string='Section 19 Gazette Page / धारा 19 राजपत्र पृष्ठ', tracking=True)
    section19_newspaper_1_name = fields.Char(string='Section 19 Newspaper 1 Name', tracking=True)
    section19_newspaper_1_date = fields.Date(string='Section 19 Newspaper 1 Date', tracking=True)
    section19_newspaper_2_name = fields.Char(string='Section 19 Newspaper 2 Name', tracking=True)
    section19_newspaper_2_date = fields.Date(string='Section 19 Newspaper 2 Date', tracking=True)
    section19_munadi_date = fields.Date(string='Section 19 Munadi Date', tracking=True)
    
    section21_notice_date = fields.Date(string='Section 21 Notice Date / धारा 21 नोटिस दिनांक', tracking=True)
    section21_hearing_date = fields.Date(string='Section 21 Hearing Date / धारा 21 सुनवाई दिनांक', tracking=True)
    
    # Compensation Details
    total_compensation_amount = fields.Float(string='Total Compensation Amount / कुल मुआवजा राशि',
                                              digits=(16, 2), tracking=True,
                                              compute='_compute_total_compensation', store=True)
    compensation_amount_text = fields.Char(string='Compensation Amount (Text) / मुआवजा राशि (पाठ)',
                                          tracking=True,
                                          help='Amount in words, e.g., उन्नीस लाख चौसठ हजार सात सौ बियालीस रुपये मात्र')
    
    # Detailed Compensation Lines (One2many)
    compensation_line_ids = fields.One2many('bhu.draft.award.compensation.line', 'award_id',
                                            string='Compensation Details / मुआवजा विवरण', tracking=True)
    
    # Displacement
    is_displacement_involved = fields.Boolean(string='Is Displacement Involved? / क्या विस्थापन शामिल है?',
                                              default=False, tracking=True)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Award / हस्ताक्षरित अवार्ड')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है',
                                         compute='_compute_has_signed_document', store=True)
    
    # Officer signature
    officer_signature = fields.Binary(string='Officer Signature / अधिकारी हस्ताक्षर')
    officer_signature_filename = fields.Char(string='Signature File Name')
    officer_name = fields.Char(string='Officer Name / अधिकारी का नाम', tracking=True,
                               default='अनुविभागीय अधिकारी (राजस्व) एवं अनुविभागीय अधिकारी (भू-अर्जन) रायगढ़')
    officer_designation = fields.Char(string='Officer Designation / अधिकारी का पद', tracking=True)
    
    # UUID for QR code
    award_uuid = fields.Char(string='Award UUID', copy=False, readonly=True, index=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
        ('signed', 'Signed / हस्ताक्षरित'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    _sql_constraints = [
        ('unique_village_project', 'UNIQUE(village_id, project_id)', 
         'Only one Draft Award can be created per village per project! / प्रति ग्राम प्रति परियोजना केवल एक अवार्ड बनाया जा सकता है!')
    ]
    
    @api.depends('signed_document_file')
    def _compute_has_signed_document(self):
        for record in self:
            record.has_signed_document = bool(record.signed_document_file)
            # Auto-sign when signed document is uploaded
            if record.has_signed_document and record.state != 'signed':
                record.state = 'signed'
                if not record.signed_date:
                    record.signed_date = fields.Date.today()
    
    @api.depends('village_id')
    def _compute_location(self):
        """Compute district and tehsil from village"""
        for record in self:
            if record.village_id:
                record.district_id = record.village_id.district_id.id if record.village_id.district_id else False
                record.tehsil_id = record.village_id.tehsil_id.id if record.village_id.tehsil_id else False
            else:
                record.district_id = False
                record.tehsil_id = False
    
    @api.depends('village_id', 'project_id')
    def _compute_section11_report(self):
        """Find Section 11 report for this village and project"""
        for record in self:
            if record.village_id and record.project_id:
                section11 = self.env['bhu.section11.preliminary.report'].search([
                    ('village_id', '=', record.village_id.id),
                    ('project_id', '=', record.project_id.id),
                    ('state', 'in', ['generated', 'signed'])
                ], limit=1, order='create_date desc')
                record.section11_report_id = section11.id if section11 else False
            else:
                record.section11_report_id = False
    
    @api.depends('village_id', 'project_id')
    def _compute_section19_notification(self):
        """Find Section 19 notification for this village and project"""
        for record in self:
            if record.village_id and record.project_id:
                section19 = self.env['bhu.section19.notification'].search([
                    ('village_ids', 'in', [record.village_id.id]),
                    ('project_id', '=', record.project_id.id),
                    ('state', 'in', ['generated', 'signed'])
                ], limit=1, order='create_date desc')
                record.section19_notification_id = section19.id if section19 else False
            else:
                record.section19_notification_id = False
    
    @api.depends('village_id', 'project_id')
    def _compute_respondents(self):
        """Compute respondents (landowners) from Section 11 land parcels"""
        for record in self:
            if record.section11_report_id and record.section11_report_id.land_parcel_ids:
                # Get all surveys for the khasras in Section 11
                khasra_numbers = record.section11_report_id.land_parcel_ids.mapped('khasra_number')
                surveys = self.env['bhu.survey'].search([
                    ('village_id', '=', record.village_id.id),
                    ('project_id', '=', record.project_id.id),
                    ('khasra_number', 'in', khasra_numbers),
                    ('state', '=', 'locked')
                ])
                # Get unique landowners from these surveys
                landowner_ids = surveys.mapped('landowner_ids')
                record.respondent_ids = landowner_ids
            else:
                record.respondent_ids = False
    
    @api.depends('land_parcel_ids.area_hectares', 'land_parcel_ids.khasra_number')
    def _compute_total_land_area(self):
        """Compute total land area and khasra count from land parcels"""
        for record in self:
            record.total_land_area = sum(record.land_parcel_ids.mapped('area_hectares'))
            record.total_khasra_count = len([p for p in record.land_parcel_ids if p.khasra_number])
    
    @api.depends('compensation_line_ids.payable_compensation_amount')
    def _compute_total_compensation(self):
        """Compute total compensation from compensation lines"""
        for record in self:
            record.total_compensation_amount = sum(record.compensation_line_ids.mapped('payable_compensation_amount'))
    
    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_land_parcels(self):
        """Auto-populate land parcels from Section 11 when village/project changes"""
        self._populate_land_parcels_from_section11()
    
    def _populate_land_parcels_from_section11(self):
        """Helper method to populate land parcels from Section 11 report"""
        self.ensure_one()
        if not self.village_id or not self.project_id:
            return
        
        # Find Section 11 report
        section11 = self.env['bhu.section11.preliminary.report'].search([
            ('village_id', '=', self.village_id.id),
            ('project_id', '=', self.project_id.id),
            ('state', 'in', ['generated', 'signed'])
        ], limit=1, order='create_date desc')
        
        if not section11 or not section11.land_parcel_ids:
            return
        
        # Clear existing land parcels
        self.land_parcel_ids = [(5, 0, 0)]
        
        # Create land parcel records from Section 11
        parcel_vals = []
        for parcel in section11.land_parcel_ids:
            parcel_vals.append((0, 0, {
                'khasra_number': parcel.khasra_number or '',
                'area_hectares': parcel.area_in_hectares or 0.0,
            }))
        
        # Set the land parcels
        if parcel_vals:
            self.land_parcel_ids = parcel_vals
        
        # Auto-populate compensation lines after land parcels are set
        self._populate_compensation_lines()
    
    def _populate_compensation_lines(self):
        """Helper method to populate compensation lines from land parcels and surveys"""
        self.ensure_one()
        if not self.land_parcel_ids:
            return
        
        # Clear existing compensation lines
        self.compensation_line_ids = [(5, 0, 0)]
        
        # Get all surveys for the khasras in land parcels
        khasra_numbers = self.land_parcel_ids.mapped('khasra_number')
        surveys = self.env['bhu.survey'].search([
            ('village_id', '=', self.village_id.id),
            ('project_id', '=', self.project_id.id),
            ('khasra_number', 'in', khasra_numbers),
            ('state', '=', 'locked')
        ])
        
        # Create compensation line for each survey
        line_vals = []
        serial = 1
        for survey in surveys:
            # Get land parcel for this khasra
            parcel = self.land_parcel_ids.filtered(lambda p: p.khasra_number == survey.khasra_number)
            if not parcel:
                continue
            
            # Create a line for each landowner
            for landowner in survey.landowner_ids:
                # Determine land type
                is_irrigated = survey.irrigation_type == 'irrigated'
                is_unirrigated = survey.irrigation_type == 'unirrigated'
                
                line_vals.append((0, 0, {
                    'serial_number': serial,
                    'landowner_id': landowner.id,
                    'khasra_number': survey.khasra_number or '',
                    'acquired_area': parcel[0].area_hectares or 0.0,
                    'is_irrigated': is_irrigated,
                    'is_unirrigated': is_unirrigated,
                    'is_fallow': False,  # Default, can be updated manually
                    'total_held_khasra': survey.khasra_number or '',
                    'total_held_area': survey.total_area or 0.0,
                    'acquired_revenue': 0.0,  # Can be updated manually
                }))
                serial += 1
        
        # Set the compensation lines
        if line_vals:
            self.compensation_line_ids = line_vals
    
    @api.model
    def _default_project_id(self):
        """Default project_id to PROJ01 if it exists"""
        project = self.env['bhu.project'].search([('code', '=', 'PROJ01')], limit=1)
        if project:
            return project.id
        fallback_project = self.env['bhu.project'].search([], limit=1)
        return fallback_project.id if fallback_project else False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create records with batch support"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.draft.award') or 'New'
            # Generate UUID if not provided
            if not vals.get('award_uuid'):
                vals['award_uuid'] = str(uuid.uuid4())
            # Set default project_id if not provided
            if not vals.get('project_id'):
                project_id = self._default_project_id()
                if project_id:
                    vals['project_id'] = project_id
        records = super().create(vals_list)
        # Auto-populate land parcels after creation if village and project are set
        for record in records:
            if record.village_id and record.project_id:
                record._populate_land_parcels_from_section11()
        return records
    
    def get_qr_code_data(self):
        """Generate QR code data for the award"""
        try:
            import qrcode
            import io
            import base64
            
            # Ensure UUID exists
            if not self.award_uuid:
                self.write({'award_uuid': str(uuid.uuid4())})
            
            # Generate QR code URL - using award UUID
            qr_url = f"https://bhuarjan.com/bhuarjan/draftaward/{self.award_uuid}/download"
            
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
        except Exception as e:
            return None
    
    def action_populate_compensation(self):
        """Manually populate compensation lines"""
        self.ensure_one()
        if not self.land_parcel_ids:
            raise ValidationError(_('Please populate land parcels first from Section 11.'))
        self._populate_compensation_lines()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Compensation lines have been populated.'),
                'type': 'success',
            }
        }
    
    def action_generate_pdf(self):
        """Generate Draft Award PDF"""
        self.ensure_one()
        # Ensure compensation lines are populated before generating PDF
        if not self.compensation_line_ids and self.land_parcel_ids:
            self._populate_compensation_lines()
        self.state = 'generated'
        return self.env.ref('bhuarjan.action_report_draft_award').report_action(self)
    
    def action_generate_notices(self):
        """Generate Notices for this award"""
        self.ensure_one()
        # Open wizard to generate notices
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Notices / नोटिस जेनरेट करें',
            'res_model': 'bhu.generate.notices.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_village_ids': [(6, 0, [self.village_id.id])] if self.village_id else [],
            }
        }
    
    def action_download_notices(self):
        """Download Notices for this award"""
        self.ensure_one()
        # Open wizard to download notices
        return {
            'type': 'ir.actions.act_window',
            'name': 'Download Notices / नोटिस डाउनलोड करें',
            'res_model': 'bhu.download.notices.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_village_id': self.village_id.id if self.village_id else False,
            }
        }
    
    def action_mark_signed(self):
        """Mark award as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()


class DraftAwardLandParcel(models.Model):
    _name = 'bhu.draft.award.land.parcel'
    _description = 'Draft Award Land Parcel'
    _order = 'khasra_number'

    award_id = fields.Many2one('bhu.draft.award', string='Award', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True)
    area_hectares = fields.Float(string='Area (Hectares) / रकबा (हेक्टेयर में)', required=True, digits=(16, 4))


class DraftAwardCompensationLine(models.Model):
    _name = 'bhu.draft.award.compensation.line'
    _description = 'Draft Award Compensation Line / अवार्ड मुआवजा पंक्ति'
    _order = 'serial_number, khasra_number'

    award_id = fields.Many2one('bhu.draft.award', string='Award', required=True, ondelete='cascade')
    
    # Serial Number
    serial_number = fields.Integer(string='Serial Number / क्र.', required=True, default=1)
    
    # Landowner Details
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner / भूमिस्वामी', required=True)
    landowner_name = fields.Char(string='Landowner Name / भूमिस्वामी का नाम', related='landowner_id.name', store=True, readonly=True)
    father_husband_name = fields.Char(string='Father/Husband Name / पिता/पति का नाम', compute='_compute_father_husband_name', store=True)
    caste = fields.Char(string='Caste / जाति', tracking=True, help='Enter caste information')
    
    @api.depends('landowner_id')
    def _compute_father_husband_name(self):
        """Compute father/husband name from landowner"""
        for record in self:
            if record.landowner_id:
                # Use father_name if available, otherwise spouse_name
                record.father_husband_name = record.landowner_id.father_name or record.landowner_id.spouse_name or ''
            else:
                record.father_husband_name = ''
    
    # Total Held Land / कुल धारित भूमि
    total_held_khasra = fields.Char(string='Total Held Khasra / कुल धारित ख.न.')
    total_held_area = fields.Float(string='Total Held Area (Hectares) / कुल धारित रकबा (हेक्टेयर)', digits=(16, 4))
    total_held_revenue = fields.Float(string='Total Held Revenue / कुल धारित लगान', digits=(16, 2))
    
    # Acquired Land Details / अर्जित भूमि का विवरण
    khasra_number = fields.Char(string='Acquired Khasra Number / अर्जित ख.न.', required=True)
    acquired_area = fields.Float(string='Acquired Area (Hectares) / अर्जित रकबा (हेक्टेयर)', required=True, digits=(16, 4))
    acquired_revenue = fields.Float(string='Acquired Revenue / अर्जित लगान', digits=(16, 2))
    
    # Land Type / अर्जित भूमि का प्रकार
    is_fallow = fields.Boolean(string='Fallow / पड़त', default=False)
    is_unirrigated = fields.Boolean(string='Unirrigated / असिंचित', default=False)
    is_irrigated = fields.Boolean(string='Irrigated / सिंचित', default=False)
    
    # Guide Line Compensation / गाईड लाइन मुआवजा
    guideline_rate_per_hectare = fields.Float(string='Guide Line Rate per Hectare / गाईड लाइन दर प्रति हेक्टेयर',
                                               digits=(16, 2), help='Guide Line March 2023-2024')
    guideline_compensation_value = fields.Float(string='Guide Line Compensation Value / गाईड लाइन मूल्य',
                                                digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Market Value Calculations / बाजार मूल्य गणना
    market_value = fields.Float(string='Market Value / मूल्य', digits=(16, 2), compute='_compute_compensation', store=True)
    market_value_factor_2 = fields.Float(string='Market Value x (Factor-2) / बाजार मूल्य x (कारक-2)',
                                         digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Solatium / सोलेशियम
    solatium_percentage = fields.Float(string='Solatium Percentage / सोलेशियम प्रतिशत', default=100.0, digits=(5, 2))
    solatium_amount = fields.Float(string='100% Solatium Amount / 100% सोलेशियम की राशि',
                                   digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Interest / ब्याज
    interest_start_date = fields.Date(string='Interest Start Date / ब्याज प्रारंभ दिनांक')
    interest_end_date = fields.Date(string='Interest End Date / ब्याज समाप्ति दिनांक')
    interest_months = fields.Integer(string='Interest Months / ब्याज माह', compute='_compute_interest_months', store=True)
    interest_rate = fields.Float(string='Interest Rate / ब्याज दर', default=30.0, digits=(5, 2),
                                 help='Interest rate as per Section 30(3)')
    interest_amount = fields.Float(string='Interest Amount / ब्याज राशि', digits=(16, 2),
                                   compute='_compute_compensation', store=True)
    
    # Total Determined Compensation / कुल निर्धारित मुआवजा
    total_determined_compensation = fields.Float(string='Total Determined Compensation / कुल निर्धारित मुआवजा',
                                                  digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Rehabilitation Policy / पुनर्वास नीति
    rehab_policy_rate_per_acre = fields.Float(string='Rehab Policy Rate per Acre / पुनर्वास नीति दर प्रति एकड़',
                                              digits=(16, 2))
    rehab_policy_compensation = fields.Float(string='Rehab Policy Compensation / पुनर्वास नीति मुआवजा',
                                             digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Payable Compensation / देय मुआवजा
    payable_compensation_amount = fields.Float(string='Payable Compensation / देय मुआवजा राशि',
                                             digits=(16, 2), compute='_compute_compensation', store=True)
    
    # Remarks / रिमार्क
    remark = fields.Text(string='Remark / रिमार्क')
    
    @api.depends('interest_start_date', 'interest_end_date')
    def _compute_interest_months(self):
        """Compute interest months from start and end dates"""
        for record in self:
            if record.interest_start_date and record.interest_end_date:
                delta = relativedelta(record.interest_end_date, record.interest_start_date)
                record.interest_months = delta.years * 12 + delta.months
            else:
                record.interest_months = 0
    
    @api.depends('acquired_area', 'guideline_rate_per_hectare', 'market_value_factor_2', 
                 'solatium_percentage', 'interest_rate', 'interest_months', 'market_value',
                 'rehab_policy_rate_per_acre')
    def _compute_compensation(self):
        """Compute all compensation amounts"""
        for record in self:
            # Guide Line Compensation Value
            if record.acquired_area and record.guideline_rate_per_hectare:
                record.guideline_compensation_value = record.acquired_area * record.guideline_rate_per_hectare
            else:
                record.guideline_compensation_value = 0.0
            
            # Market Value (use guideline value as base)
            record.market_value = record.guideline_compensation_value
            
            # Market Value x Factor-2
            record.market_value_factor_2 = record.market_value * 2.0
            
            # Solatium (100% of market value factor-2)
            record.solatium_amount = record.market_value_factor_2 * (record.solatium_percentage / 100.0)
            
            # Interest (on market value factor-2, as per Section 30(3))
            if record.interest_months > 0 and record.interest_rate > 0:
                monthly_rate = record.interest_rate / 12.0
                record.interest_amount = record.market_value_factor_2 * (monthly_rate / 100.0) * record.interest_months
            else:
                record.interest_amount = 0.0
            
            # Total Determined Compensation
            record.total_determined_compensation = (record.market_value_factor_2 + 
                                                     record.solatium_amount + 
                                                     record.interest_amount)
            
            # Rehabilitation Policy Compensation (convert hectares to acres: 1 hectare = 2.47105 acres)
            if record.acquired_area and record.rehab_policy_rate_per_acre:
                area_in_acres = record.acquired_area * 2.47105
                record.rehab_policy_compensation = area_in_acres * record.rehab_policy_rate_per_acre
            else:
                record.rehab_policy_compensation = 0.0
            
            # Payable Compensation (higher of total determined or rehab policy)
            record.payable_compensation_amount = max(record.total_determined_compensation, 
                                                    record.rehab_policy_compensation)


class GenerateNoticesWizard(models.TransientModel):
    _name = 'bhu.generate.notices.wizard'
    _description = 'Generate Notices Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages')

    def action_generate_notices(self):
        """Generate Notices - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notice generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DownloadNoticesWizard(models.TransientModel):
    _name = 'bhu.download.notices.wizard'
    _description = 'Download Notices Wizard'

    project_id = fields.Many2one('bhu.project', string='Project')
    village_id = fields.Many2one('bhu.village', string='Village')
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner')

    def action_download_notices(self):
        """Download Notices - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Notice download will be implemented soon.'),
                'type': 'info',
            }
        }


class AwardNotificationWizard(models.TransientModel):
    _name = 'bhu.award.notification.wizard'
    _description = 'Award Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_award_notification(self):
        """Generate Award Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Award notification generation will be implemented soon.'),
                'type': 'info',
            }
        }


class DownloadAwardNotificationWizard(models.TransientModel):
    _name = 'bhu.download.award.notification.wizard'
    _description = 'Download Award Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project')
    village_id = fields.Many2one('bhu.village', string='Village')
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner')

    def action_download_award_notification(self):
        """Download Award Notification - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Award notification download will be implemented soon.'),
                'type': 'info',
            }
        }


class GeneratePaymentFileWizard(models.TransientModel):
    _name = 'bhu.generate.payment.file.wizard'
    _description = 'Generate Payment File Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_payment_file(self):
        """Generate Payment File - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Payment file generation will be implemented soon.'),
                'type': 'info',
            }
        }

