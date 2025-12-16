# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid

import json

class Section19Notification(models.Model):
    _name = 'bhu.section19.notification'
    _description = 'Section 19 Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.notification.mixin', 'bhu.process.workflow.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Notification Name / अधिसूचना का नाम', default='New', tracking=True, readonly=True)
    
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=False, tracking=True, ondelete='cascade',
                                  default=lambda self: self._default_project_id())
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # District, Tehsil - computed from villages
    district_id = fields.Many2one('bhu.district', string='District / जिला', compute='_compute_location', store=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', compute='_compute_location', store=True)
    
    # Public Purpose
    public_purpose = fields.Text(string='Public Purpose / लोक प्रयोजन', 
                                 help='Description of public purpose for land acquisition', tracking=True)
    
    # Schedule/Table - Land Parcels (One2many)
    land_parcel_ids = fields.One2many('bhu.section19.land.parcel', 'notification_id', 
                                      string='Land Parcels / भूमि खंड', tracking=True)
    
    
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
    
    # State field is inherited from mixin
    
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
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain to only show project villages"""
        # Only reset village if it's not valid for the new project
        if self.project_id and self.project_id.village_ids:
            # If village is already set and is in the project's villages, keep it
            if self.village_id and self.village_id.id in self.project_id.village_ids.ids:
                # Village is valid, keep it
                pass
            else:
                # Village is not valid for this project, reset it
                self.village_id = False
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            # No villages in project, reset village
            self.village_id = False
            return {'domain': {'village_id': [('id', '=', False)]}}
    
    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_surveys(self):
        """Auto-populate land parcels from Section 11 approved khasras (excluding objections) when village is selected"""
        if self.village_id and self.project_id:
            self._populate_land_parcels_from_surveys()
    
    def _populate_land_parcels_from_surveys(self):
        """Helper method to populate land parcels from Section 11 approved khasras, excluding those with objections"""
        self.ensure_one()
        if not self.village_id or not self.project_id:
            return
        
        # Get all Section 11 Preliminary Reports for selected village and project (approved/generated)
        section11_reports = self.env['bhu.section11.preliminary.report'].search([
            ('village_id', '=', self.village_id.id),
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
        # Exclude resolved objections (those with resolved_date set)
        objections = self.env['bhu.section15.objection'].search([
            ('project_id', '=', self.project_id.id),
            ('village_id', '=', self.village_id.id),
            ('resolved_date', '=', False)  # Exclude resolved objections
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
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        # Get defaults from context (set by dashboard or other actions)
        if 'default_project_id' in self.env.context:
            res['project_id'] = self.env.context['default_project_id']
        if 'default_village_id' in self.env.context:
            res['village_id'] = self.env.context['default_village_id']
        
        return res
    
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
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    try:
                        sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                            'section19_notification', project_id, village_id=village_id
                        )
                        if sequence_number:
                            vals['name'] = sequence_number
                        else:
                            # Fallback to ir.sequence
                            vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section19.notification') or 'New'
                    except:
                        # Fallback to ir.sequence
                        vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section19.notification') or 'New'
                else:
                    # No project_id, use fallback
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
        # Auto-populate land parcels after creation
        for record in records:
            if record.village_id and record.project_id:
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
    
    # Override mixin method to generate Section 19 PDF
    def action_download_unsigned_file(self):
        """Generate and download Section 19 Notification PDF (unsigned) - Override mixin"""
        self.ensure_one()
        return self.env.ref('bhuarjan.action_report_section19_notification').report_action(self)
    
    def action_generate_pdf(self):
        """Generate Section 19 Notification PDF - Legacy method"""
        return self.action_download_unsigned_file()
    
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
    
    # Additional fields from Section 11
    survey_number = fields.Char(string='Survey Number / सर्वे नंबर')
    survey_date = fields.Date(string='Survey Date / सर्वे दिनांक')
    survey_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
        ('rejected', 'Rejected'),
    ], string='Survey Status / सर्वे स्थिति')
    
    # Location fields
    district_id = fields.Many2one('bhu.district', string='District / जिला')
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम')
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना')
    
    # Additional details
    authorized_officer = fields.Char(string='Authorized Officer / प्राधिकृत अधिकारी',
                                    help='Officer authorized by Section 12')
    public_purpose_description = fields.Text(string='Public Purpose Description / लोक प्रयोजन विवरण')


class Section19NotificationWizard(models.TransientModel):
    _name = 'bhu.section19.notification.wizard'
    _description = 'Section 19 Notification Wizard'

    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True)
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village when project changes and set domain to only show project villages"""
        # Only reset village if it's not valid for the new project
        if self.project_id and self.project_id.village_ids:
            # If village is already set and is in the project's villages, keep it
            if self.village_id and self.village_id.id in self.project_id.village_ids.ids:
                # Village is valid, keep it
                pass
            else:
                # Village is not valid for this project, reset it
                self.village_id = False
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            # No villages in project, reset village
            self.village_id = False
            return {'domain': {'village_id': [('id', '=', False)]}}
    
    def action_generate_notification(self):
        """Create Section 19 Notification record and generate PDF"""
        self.ensure_one()
        
        # Create notification record
        notification = self.env['bhu.section19.notification'].create({
            'project_id': self.project_id.id,
            'village_id': self.village_id.id,
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




