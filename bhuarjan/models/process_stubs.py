# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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


class DraftAwardWizard(models.TransientModel):
    _name = 'bhu.draft.award.wizard'
    _description = 'Draft Award Wizard'

    project_id = fields.Many2one('bhu.project', string='Project', required=True)
    village_ids = fields.Many2many('bhu.village', string='Villages', required=True)

    def action_generate_draft_award(self):
        """Generate Draft Award - To be implemented"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Draft award generation will be implemented soon.'),
                'type': 'info',
            }
        }


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

