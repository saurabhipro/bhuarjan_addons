# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from . import utils
import uuid


# Stub models for Process menu items - to be implemented later
# These are minimal models to allow the module to load

class Section4Notification(models.Model):
    _name = 'bhu.section4.notification'
    _description = 'Section 4 Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.notification.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Notification Name / अधिसूचना का नाम', required=True, default='New', tracking=True)
    notification_seq_number = fields.Char(string='Notification Sequence Number', readonly=True, tracking=True, 
                                          help='Sequence number for this notification')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=False, tracking=True, 
                                  default=lambda self: self._default_project_id())
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    _sql_constraints = [
        ('unique_village_project', 'UNIQUE(village_id, project_id)', 
         'Only one Section 4 Notification can be created per village per project!')
    ]
    
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
    
    
    # UUID for QR code
    notification_uuid = fields.Char(string='Notification UUID', copy=False, readonly=True, index=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
        ('signed', 'Signed / हस्ताक्षरित'),
        ('notification_11', 'Notification 11 / अधिसूचना 11'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('signed_document_file', 'state', 'signed_date')
    def _compute_has_signed_document(self):
        for record in self:
            # Consider it signed if there's a signed document file OR if state is 'signed'
            record.has_signed_document = bool(record.signed_document_file) or record.state == 'signed'
    
    @api.onchange('signed_document_file')
    def _onchange_signed_document_file(self):
        """Auto-change status to 'signed' when signed document is uploaded"""
        if self.signed_document_file and self.state != 'signed':
            self.state = 'signed'
            if not self.signed_date:
                self.signed_date = fields.Date.today()
    
    @api.depends('project_id', 'village_id')
    def _compute_survey_ids(self):
        """Compute surveys for selected village and project"""
        for record in self:
            if record.project_id and record.village_id:
                surveys = self.env['bhu.survey'].search([
                    ('project_id', '=', record.project_id.id),
                    ('village_id', '=', record.village_id.id)
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
    
    @api.depends('project_id', 'village_id')
    def _compute_has_section11(self):
        """Check if Section 11 Preliminary Report exists for the village"""
        for record in self:
            if record.project_id and record.village_id:
                section11_reports = self.env['bhu.section11.preliminary.report'].search([
                    ('project_id', '=', record.project_id.id),
                    ('village_id', '=', record.village_id.id)
                ], limit=1)
                record.has_section11 = bool(section11_reports)
            else:
                record.has_section11 = False
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain"""
        self.village_id = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_id': []}}
    
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
        existing_records = []
        new_vals_list = []
        
        for vals in vals_list:
            project_id = vals.get('project_id')
            village_id = vals.get('village_id')
            
            # Check for existing records to prevent UniqueViolation
            # Skip this check during data loading - let Odoo's mechanism handle it
            is_data_loading = self.env.context.get('install_mode') or self.env.context.get('load') or \
                             self.env.context.get('module') or '_force_unlink' in self.env.context
            if project_id and village_id and not is_data_loading:
                existing = self.env['bhu.section4.notification'].search([
                    ('project_id', '=', project_id),
                    ('village_id', '=', village_id)
                ], limit=1)
                if existing:
                    # In normal create, return existing to prevent duplicate
                    existing_records.append(existing)
                    continue
            
            # Generate sequence number for both name and notification_seq_number
            sequence_number = None
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                # Try to use sequence settings from settings master
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section4_notification', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section4.notification') or 'New'
                        sequence_number = vals['name']
                else:
                    # No project_id, use fallback
                    vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section4.notification') or 'New'
                    sequence_number = vals['name']
            else:
                # If name is provided, use it as sequence number
                sequence_number = vals.get('name')
            
            # Auto-generate notification sequence number if not provided (use same as name)
            if not vals.get('notification_seq_number') and sequence_number:
                vals['notification_seq_number'] = sequence_number
            
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
            new_vals_list.append(vals)
        
        # Create new records
        if new_vals_list:
            records = super().create(new_vals_list)
        else:
            records = self.env['bhu.section4.notification']
        
        if existing_records:
            records = records | self.env['bhu.section4.notification'].browse([r.id for r in existing_records])
        
        return records
    
    def _get_consolidated_village_data(self):
        """Get consolidated survey data for the village"""
        self.ensure_one()
        
        # Get all approved or locked surveys for the selected village in the project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ('approved', 'locked'))
        ])
        
        # Return data for the single village
        if self.village_id and surveys:
            district_name = self.village_id.district_id.name if self.village_id.district_id else 'Raigarh (Chhattisgarh)'
            tehsil_name = self.village_id.tehsil_id.name if self.village_id.tehsil_id else ''
            
            total_area = sum(surveys.mapped('acquired_area'))
            
            return [{
                'village_id': self.village_id.id,
                'village_name': self.village_id.name,
                'district': district_name,
                'tehsil': tehsil_name,
                'total_area': total_area,
                'surveys': surveys.ids
            }]
        
        return []
    
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
        
        # Validate that all surveys for selected village are approved
        if not self.project_id or not self.village_id:
            raise ValidationError(_('Please select a project and village.'))
        
        # Get all surveys for selected village
        all_surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id)
        ])
        
        if not all_surveys:
            raise ValidationError(_('No surveys found for the selected village. Please create surveys first.'))
        
        # Check if all surveys are approved or locked (treat locked as approved)
        non_approved_surveys = all_surveys.filtered(lambda s: s.state not in ('approved', 'locked'))
        if non_approved_surveys:
            raise ValidationError(_(
                'Cannot generate Section 4 Notification. Some surveys are not approved yet.\n\n'
                'Please approve all surveys before generating the notification.'
            ))
        
        self.state = 'generated'
        
        # Lock all approved surveys for the selected village (skip already locked ones)
        approved_surveys = all_surveys.filtered(lambda s: s.state == 'approved')
        if approved_surveys:
            approved_surveys.write({'state': 'locked'})
            self.message_post(
                body=_('Locked %d survey(s) for village: %s') % (
                    len(approved_surveys),
                    self.village_id.name
                )
            )
        
        # Use wizard to generate PDF (reuse existing logic)
        # Always create a fresh wizard with current data to ensure report has all data
        wizard = self.env['bhu.section4.notification.wizard'].create({
            'project_id': self.project_id.id,
            'village_id': self.village_id.id,
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
    
    def action_download_pdf(self):
        """Download Section 4 Notification PDF (for generated/signed/notification_11 notifications)"""
        self.ensure_one()
        
        if self.state not in ('generated', 'signed', 'notification_11'):
            raise ValidationError(_('Notification must be generated before downloading.'))
        
        # If signed document exists, download it
        if self.signed_document_file:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/bhu.section4.notification/{self.id}/signed_document_file/{self.signed_document_filename or "signed_notification.pdf"}?download=true',
                'target': 'self',
            }
        
        # Otherwise, generate PDF using wizard (same as action_generate_pdf but for download)
        wizard = self.env['bhu.section4.notification.wizard'].create({
            'project_id': self.project_id.id,
            'village_id': self.village_id.id,
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


class Section4NotificationWizard(models.TransientModel):
    _name = 'bhu.section4.notification.wizard'
    _description = 'Section 4 Notification Wizard'
    _inherit = ['bhu.notification.mixin']

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)
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
        """Reset village when project changes and set domain"""
        self.village_id = False
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_id': []}}

    def _get_consolidated_village_data(self):
        """Get consolidated survey data for the village"""
        self.ensure_one()
        
        # Get all approved or locked surveys for the selected village in the project
        surveys = self.env['bhu.survey'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('state', 'in', ('approved', 'locked'))
        ])
        
        # Return data for the single village
        if self.village_id and surveys:
            district_name = self.village_id.district_id.name if self.village_id.district_id else 'Raigarh (Chhattisgarh)'
            tehsil_name = self.village_id.tehsil_id.name if self.village_id.tehsil_id else ''
            
            total_area = sum(surveys.mapped('acquired_area'))
            
            return [{
                'village_id': self.village_id.id,
                'village_name': self.village_id.name,
                'district': district_name,
                'tehsil': tehsil_name,
                'total_area': total_area,
                'surveys': surveys.ids
            }]
        
        return []

    def get_formatted_hearing_date(self):
        """Format public hearing date for display"""
        self.ensure_one()
        if self.public_hearing_date:
            return self.public_hearing_date.strftime('%d/%m/%Y')
        return '........................'
    
    
    def action_generate_pdf(self):
        """Generate Section 4 Notification PDF and create notification record"""
        self.ensure_one()
        
        if not self.village_id:
            raise ValidationError(_('Please select a village.'))
        
        # Get consolidated data
        consolidated_data = self._get_consolidated_village_data()
        
        if not consolidated_data:
            raise ValidationError(_('No approved surveys found for the selected village.'))
        
        # Create notification record
        notification = self.env['bhu.section4.notification'].create({
            'project_id': self.project_id.id,
            'village_id': self.village_id.id,
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

