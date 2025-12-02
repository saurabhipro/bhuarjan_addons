# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid

class Section11PreliminaryReport(models.Model):
    _name = 'bhu.section11.preliminary.report'
    _description = 'Section 11 Preliminary Report'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.notification.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Report Name', required=True, default='New', tracking=True, readonly=True)
    project_id = fields.Many2one('bhu.project', string='Project', required=True, tracking=True, ondelete='cascade',
                                  default=lambda self: self._default_project_id())
    village_ids = fields.Many2many('bhu.village', string='Villages / ग्राम', required=True, tracking=True)
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Auto-populate villages when project is selected"""
        # Auto-populate villages with all project villages when project is selected
        if self.project_id and self.project_id.village_ids:
            # Always populate with project villages when project is selected
            self.village_ids = self.project_id.village_ids
        else:
            self.village_ids = False
        
        # Set domain to only show project villages
        if self.project_id and self.project_id.village_ids:
            return {'domain': {'village_ids': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            return {'domain': {'village_ids': [('id', '=', False)]}}
    
    # Section 4 Notification reference
    section4_notification_id = fields.Many2one('bhu.section4.notification', string='Section 4 Notification',
                                               tracking=True, help='Select Section 4 Notification to auto-populate survey details')
    
    # Notification Details
    notification_number = fields.Char(string='Notification Number', tracking=True)
    publication_date = fields.Date(string='Publication Date', tracking=True)
    
    # Computed fields from Form 10 surveys
    total_khasras_count = fields.Integer(string='Total Khasras Count / कुल खसरा संख्या',
                                         compute='_compute_project_statistics', store=False)
    total_area_acquired = fields.Float(string='Total Area Acquired (Hectares) / रकबा (हेक्टेयर)',
                                       compute='_compute_project_statistics', store=False,
                                       digits=(16, 4))
    
    # Schedule/Table - Land Parcels (One2many)
    land_parcel_ids = fields.One2many('bhu.section11.land.parcel', 'report_id', 
                                      string='Land Parcels', tracking=True)
    
    # Computed fields for list view
    khasra_numbers = fields.Char(string='Khasra Numbers', compute='_compute_khasra_info', store=False)
    khasra_count = fields.Integer(string='Khasra Count', compute='_compute_khasra_info', store=False)
    survey_numbers = fields.Char(string='Survey Numbers', compute='_compute_survey_info', store=False)
    survey_date = fields.Date(string='Survey Date', compute='_compute_survey_info', store=False)
    
    @api.depends('project_id', 'village_ids')
    def _compute_project_statistics(self):
        """Compute total khasras count and total area acquired from Form 10 surveys"""
        for record in self:
            if record.project_id:
                # If specific villages are selected, use those; otherwise use all project villages
                village_ids = record.village_ids.ids if record.village_ids else record.project_id.village_ids.ids
                
                if village_ids:
                    # Get all surveys for selected villages in this project
                    surveys = self.env['bhu.survey'].search([
                        ('project_id', '=', record.project_id.id),
                        ('village_id', 'in', village_ids),
                        ('khasra_number', '!=', False),
                    ])
                    
                    # Count unique khasra numbers
                    unique_khasras = set(surveys.mapped('khasra_number'))
                    record.total_khasras_count = len(unique_khasras)
                    
                    # Sum acquired area
                    record.total_area_acquired = sum(surveys.mapped('acquired_area'))
                else:
                    record.total_khasras_count = 0
                    record.total_area_acquired = 0.0
            else:
                record.total_khasras_count = 0
                record.total_area_acquired = 0.0
    
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
    
    @api.depends('village_ids', 'project_id')
    def _compute_survey_info(self):
        """Compute survey numbers and date from related surveys"""
        for record in self:
            if record.village_ids and record.project_id:
                village_ids = record.village_ids.ids
                surveys = self.env['bhu.survey'].search([
                    ('village_id', 'in', village_ids),
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
    paragraph_2_claims_info = fields.Text(string='Paragraph 2: Claims/Objections Info / धारा 2: दावे/आपत्तियों की जानकारी',
                                          help='Information about claims/objections submission (60 days deadline)',
                                          tracking=True)
    
    # Paragraph 3: Land Map Inspection
    paragraph_3_map_inspection_location = fields.Char(string='Paragraph 3: Land Map Inspection / धारा 3: भूमि मानचित्र निरीक्षण',
                                                       help='Location where land map can be inspected (SDO Revenue office)',
                                                       tracking=True)
    
    # Question 6: Officer authorized by Section 12
    question_6_authorized_officer = fields.Char(string='Question 6: Officer authorized by Section 12 / (छः) धारा 12 द्वारा प्राधिकृत अधिकारी',
                                                tracking=True,
                                                help='Officer authorized by Section 12')
    
    # Question 7: Description of public purpose
    question_7_public_purpose = fields.Text(string='Question 7: Description of public purpose / (सात) सार्वजनिक प्रयोजन का विवरण',
                                           tracking=True,
                                           help='Description of public purpose')
    
    # Question 8: Displacement (Paragraph 4)
    paragraph_4_is_displacement = fields.Boolean(string='Question 8: Is Displacement Involved? / (आठ) कितने परिवारों का विस्थापन निहित है।',
                                                 default=False, tracking=True)
    paragraph_4_affected_families_count = fields.Integer(string='Affected Families Count / प्रभावित परिवारों की संख्या',
                                                         tracking=True)
    
    # Question 9: Exemption or SIA Justification (Paragraph 5)
    paragraph_5_is_exemption = fields.Boolean(string='Question 9: Is Exemption Granted? / (नौ) क्या प्रस्तावित परियोजना के लिए अधिनियम 2013 के अध्याय "दो" एवं "तीन" के प्रावधानों से छूट प्रदान की गई है।',
                                               default=False, tracking=True)
    paragraph_5_exemption_details = fields.Text(string='Exemption Details / छूट विवरण',
                                                 help='Details of exemption notification (number, date, exempted chapters)',
                                                 tracking=True)
    paragraph_5_sia_justification = fields.Text(string='SIA Justification / SIA औचित्य',
                                                help='SIA justification details (last resort, social benefits)',
                                                tracking=True)
    
    # Question 10: Rehabilitation Administrator (Paragraph 6)
    paragraph_6_rehab_admin_name = fields.Char(string='Question 10: Rehabilitation Administrator / (दस) पुनर्वास प्रशासक',
                                               help='Name/Designation of Rehabilitation and Resettlement Administrator',
                                               tracking=True)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Report')
    signed_document_filename = fields.Char(string='Signed File Name')
    signed_date = fields.Date(string='Signed Date', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document', 
                                         compute='_compute_has_signed_document', store=True)
    
    
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
    
    @api.onchange('signed_document_file')
    def _onchange_signed_document_file(self):
        """Auto-change status to 'signed' when signed document is uploaded"""
        if self.signed_document_file and self.state != 'signed':
            self.state = 'signed'
            if not self.signed_date:
                self.signed_date = fields.Date.today()
    
    @api.onchange('village_ids', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Auto-populate land parcels when villages or project changes"""
        # Auto-populate surveys when villages or project changes
        if self.village_ids and self.project_id:
            self._populate_land_parcels_from_surveys()
    
    def _populate_land_parcels_from_surveys(self):
        """Helper method to populate land parcels from locked surveys"""
        self.ensure_one()
        if not self.village_ids or not self.project_id:
            return
        
        village_ids = self.village_ids.ids
        # Always search directly for locked surveys for the selected villages and project
        # This ensures we get the surveys even if Section 4's computed survey_ids is not ready
        locked_surveys = self.env['bhu.survey'].search([
            ('village_id', 'in', village_ids),
            ('project_id', '=', self.project_id.id),
            ('state', '=', 'locked')
        ], order='khasra_number')
        
        # If no locked surveys found, also check for approved surveys
        if not locked_surveys:
            locked_surveys = self.env['bhu.survey'].search([
                ('village_id', 'in', village_ids),
                ('project_id', '=', self.project_id.id),
                ('state', '=', 'approved')
            ], order='khasra_number')
        
        # Clear existing land parcels
        self.land_parcel_ids = [(5, 0, 0)]
        
        # Create land parcel records from locked/approved surveys
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
                'village_id': survey.village_id.id,
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
        # Check for existing records to avoid unique constraint violations
        existing_records = []
        new_vals_list = []
        
        for vals in vals_list:
            # If section4_notification_id is provided, populate project_id and village_id from it
            section4_notification_id = vals.get('section4_notification_id')
            if section4_notification_id:
                section4_notif = self.env['bhu.section4.notification'].browse(section4_notification_id)
                if section4_notif.exists():
                    # Check if Section 4 is already in 'notification_11' status - prevent recreation
                    if section4_notif.state == 'notification_11':
                        raise ValidationError(_(
                            'Notification 11 has already been generated for this Section 4 Notification (%s). '
                            'Cannot create another Notification 11 for the same village and project.'
                        ) % section4_notif.name)
                    
                    # Set project_id from Section 4 if not already set
                    if not vals.get('project_id') and section4_notif.project_id:
                        vals['project_id'] = section4_notif.project_id.id
                    # Set village_ids from Section 4 if not already set
                    if not vals.get('village_ids') and section4_notif.village_id:
                        vals['village_ids'] = [(6, 0, [section4_notif.village_id.id])]
                    # Set notification_number from Section 4 if not already set (for reference only)
                    if not vals.get('notification_number') and section4_notif.notification_seq_number:
                        vals['notification_number'] = section4_notif.notification_seq_number
                    # Don't use Section 4's name - generate new sequence number using sequence master
                    # The name will be generated below using the sequence master for section11_notification
            
            project_id = vals.get('project_id')
            village_ids = vals.get('village_ids')
            
            # Ensure required fields are set
            if not village_ids:
                # Try to get from default if available
                if not project_id:
                    project_id = self._default_project_id()
                    if project_id:
                        vals['project_id'] = project_id
                        # Auto-populate villages from project
                        project = self.env['bhu.project'].browse(project_id)
                        if project and project.village_ids:
                            vals['village_ids'] = [(6, 0, project.village_ids.ids)]
            
            # Note: Since we now support multiple villages, we don't check for existing records
            # based on village_id anymore. Each report can have multiple villages.
            
            # Generate name if needed
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                # Try to use sequence settings from settings master
                if project_id:
                    # Use first village if multiple villages selected
                    village_ids_list = vals.get('village_ids', [])
                    first_village_id = None
                    if village_ids_list and isinstance(village_ids_list[0], (list, tuple)) and len(village_ids_list[0]) > 2:
                        first_village_id = village_ids_list[0][2] if len(village_ids_list[0]) > 2 else None
                    elif isinstance(village_ids_list, list) and village_ids_list:
                        first_village_id = village_ids_list[0] if isinstance(village_ids_list[0], int) else None
                    
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'section11_notification', project_id, village_id=first_village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section11.preliminary.report') or 'New'
                else:
                    # No project_id, use fallback
                    vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section11.preliminary.report') or 'New'
            # Generate UUID if not provided
            if not vals.get('report_uuid'):
                vals['report_uuid'] = str(uuid.uuid4())
            new_vals_list.append(vals)
        
        # Create only new records
        records = super().create(new_vals_list) if new_vals_list else self.env['bhu.section11.preliminary.report']
        
        # Add existing records to the result
        if existing_records:
            records = records | self.env['bhu.section11.preliminary.report'].browse([r.id for r in existing_records])
        
        # Auto-populate land parcels after creation if villages and project are set
        # Also update Section 4 Notification status to 'notification_11'
        for record in records:
            if record.village_ids and record.project_id:
                record._populate_land_parcels_from_surveys()
            # Update Section 4 Notification status to 'notification_11' when Section 11 is created
            if record.section4_notification_id and record.section4_notification_id.state != 'notification_11':
                record.section4_notification_id.write({'state': 'notification_11'})
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
    
    def action_populate_from_surveys(self):
        """Manually populate land parcels from surveys"""
        self.ensure_one()
        if not self.village_ids or not self.project_id:
            raise ValidationError(_('Please select Villages and Project first.'))
        self._populate_land_parcels_from_surveys()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Land parcels have been populated from surveys.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_generate_pdf(self):
        """Generate Section 11 Preliminary Report PDF"""
        self.ensure_one()
        self.state = 'generated'
        # Update Section 4 Notification status to 'notification_11' when Section 11 is generated
        if self.section4_notification_id and self.section4_notification_id.state != 'notification_11':
            self.section4_notification_id.write({'state': 'notification_11'})
        report_action = self.env.ref('bhuarjan.action_report_section11_preliminary')
        return report_action.report_action(self.ids)
    
    def action_download_pdf(self):
        """Download Section 11 Preliminary Report PDF (for generated/signed notifications)"""
        self.ensure_one()
        
        if self.state not in ('generated', 'signed'):
            raise ValidationError(_('Notification must be generated before downloading.'))
        
        # Always generate PDF report (signed document download will be separate from document vault)
        report_action = self.env.ref('bhuarjan.action_report_section11_preliminary')
        return report_action.report_action(self.ids)
    
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
    
    # Related fields from report and village
    district_id = fields.Many2one('bhu.district', string='District', related='village_id.district_id', store=True, readonly=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', related='village_id.tehsil_id', store=True, readonly=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    project_id = fields.Many2one('bhu.project', string='Project', related='report_id.project_id', store=True, readonly=True)
    
    # Computed fields from related survey
    survey_number = fields.Char(string='Survey Number', compute='_compute_survey_info', store=False)
    survey_date = fields.Date(string='Survey Date', compute='_compute_survey_info', store=False)
    survey_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
        ('rejected', 'Rejected'),
    ], string='Survey Status', compute='_compute_survey_info', store=False)
    
    @api.depends('khasra_number', 'village_id', 'report_id.project_id')
    def _compute_survey_info(self):
        """Compute survey number, date, and state from related survey"""
        for record in self:
            if record.khasra_number and record.village_id and record.report_id and record.report_id.project_id:
                survey = self.env['bhu.survey'].search([
                    ('khasra_number', '=', record.khasra_number),
                    ('village_id', '=', record.village_id.id),
                    ('project_id', '=', record.report_id.project_id.id),
                    ('state', 'in', ('locked', 'approved'))
                ], limit=1)
                if survey:
                    record.survey_number = survey.name or ''
                    record.survey_date = survey.survey_date or False
                    record.survey_state = survey.state or False
                else:
                    record.survey_number = ''
                    record.survey_date = False
                    record.survey_state = False
            else:
                record.survey_number = ''
                record.survey_date = False
                record.survey_state = False


class Section19Notification(models.Model):

    _name = 'bhu.section11.preliminary.wizard'
    _description = 'Section 11 Preliminary Report Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)

    def action_generate_report(self):
        """Create Section 11 Preliminary Report record"""
        self.ensure_one()
        
        # Auto-populate villages from project
        village_ids = []
        if self.project_id and self.project_id.village_ids:
            village_ids = [(6, 0, self.project_id.village_ids.ids)]
        
        # Create the report record
        report = self.env['bhu.section11.preliminary.report'].create({
            'project_id': self.project_id.id,
            'village_ids': village_ids,
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

