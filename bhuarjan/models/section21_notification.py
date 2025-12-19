# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import uuid

class Section21Notification(models.Model):
    _name = 'bhu.section21.notification'
    _description = 'Section 21 Notification / धारा 21 अधिसूचना'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'bhu.notification.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Notification Name / अधिसूचना का नाम', default='New', tracking=True, readonly=True)
    
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=False, tracking=True, ondelete='cascade',
                                  default=lambda self: self._default_project_id())
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    
    # District, Tehsil - computed from villages
    district_id = fields.Many2one('bhu.district', string='District / जिला', compute='_compute_location', store=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', compute='_compute_location', store=True)
    
    # Notice Date
    notice_date = fields.Date(string='Notice Date / नोटिस दिनांक', tracking=True,
                              default=fields.Date.today,
                              help='Date of issue of the public notice')
    
    # Last Date for Claims and Objections
    last_date_for_claims = fields.Date(string='Last Date for Claims / दावे के लिए अंतिम दिनांक', tracking=True,
                                       help='Last date for submitting claims and objections')
    
    # Land Parcels (One2many)
    land_parcel_ids = fields.One2many('bhu.section21.land.parcel', 'notification_id', 
                                      string='Land Parcels / भूमि खंड', tracking=True)
    
    # Computed fields for list view
    khasra_numbers = fields.Char(string='Khasra Numbers / खसरा नंबर', compute='_compute_khasra_info', store=False)
    khasra_count = fields.Integer(string='Khasra Count / खसरा संख्या', compute='_compute_khasra_info', store=False)
    
    # Signed document fields
    signed_document_file = fields.Binary(string='Signed Notification / हस्ताक्षरित अधिसूचना')
    signed_document_filename = fields.Char(string='Signed File Name / हस्ताक्षरित फ़ाइल नाम')
    signed_date = fields.Date(string='Signed Date / हस्ताक्षर दिनांक', tracking=True)
    has_signed_document = fields.Boolean(string='Has Signed Document / हस्ताक्षरित दस्तावेज़ है', 
                                         compute='_compute_has_signed_document', store=True)
    
    # Collector signature
    collector_signature = fields.Binary(string='Collector Signature / कलेक्टर हस्ताक्षर')
    collector_signature_filename = fields.Char(string='Signature File Name')
    collector_name = fields.Char(string='Collector Name / कलेक्टर का नाम', tracking=True,
                                  default='कलेक्टर जिला-रायगढ़')
    
    # Additional Collector
    additional_collector_name = fields.Char(string='Additional Collector Name / अपर कलेक्टर का नाम', tracking=True,
                                           default='अपर कलेक्टर जिला-रायगढ़')
    
    # UUID for QR code
    notification_uuid = fields.Char(string='Notification UUID', copy=False, readonly=True, index=True)
    
    # State field - simple states like Section 19
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
        if self.project_id and self.project_id.village_ids:
            if self.village_id and self.village_id.id in self.project_id.village_ids.ids:
                pass
            else:
                self.village_id = False
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        else:
            self.village_id = False
            return {'domain': {'village_id': [('id', '=', False)]}}
    
    @api.onchange('village_id', 'project_id')
    def _onchange_village_populate_land_parcels(self):
        """Auto-populate land parcels from Section 19 or Draft Award when village is selected"""
        if self.village_id and self.project_id:
            self._populate_land_parcels_from_section19()
    
    def _populate_land_parcels_from_section19(self):
        """Helper method to populate land parcels from Section 19 notification"""
        self.ensure_one()
        if not self.village_id or not self.project_id:
            return
        
        # Get Section 19 notification for this village and project
        section19 = self.env['bhu.section19.notification'].search([
            ('village_id', '=', self.village_id.id),
            ('project_id', '=', self.project_id.id),
            ('state', 'in', ['generated', 'signed'])
        ], limit=1, order='create_date desc')
        
        if section19 and section19.land_parcel_ids:
            # Clear existing land parcels
            self.land_parcel_ids = [(5, 0, 0)]
            
            # Create land parcel records from Section 19
            parcel_vals = []
            for parcel in section19.land_parcel_ids:
                parcel_vals.append((0, 0, {
                    'khasra_number': parcel.khasra_number or '',
                    'area_hectares': parcel.area_hectares or 0.0,
                    'remark': '',  # Default empty remark
                }))
            
            # Set the land parcels
            if parcel_vals:
                self.land_parcel_ids = parcel_vals
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        # Get defaults from context
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
                            'section21_notification', project_id, village_id=village_id
                        )
                        if sequence_number:
                            vals['name'] = sequence_number
                        else:
                            # Fallback to ir.sequence
                            vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section21.notification') or 'New'
                    except:
                        # Fallback to ir.sequence
                        vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section21.notification') or 'New'
                else:
                    # No project_id, use fallback
                    vals['name'] = self.env['ir.sequence'].next_by_code('bhu.section21.notification') or 'New'
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
                record._populate_land_parcels_from_section19()
        return records
    
    def write(self, vals):
        """Override write to repopulate land parcels when village or project changes"""
        result = super().write(vals)
        # If village_id or project_id changed, repopulate land parcels
        if 'village_id' in vals or 'project_id' in vals:
            for record in self:
                if record.village_id and record.project_id:
                    record._populate_land_parcels_from_section19()
        return result
    
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
            qr_url = f"https://bhuarjan.com/bhuarjan/section21/{self.notification_uuid}/download"
            
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
    
    # Override mixin method to generate Section 21 PDF
    def action_download_unsigned_file(self):
        """Generate and download Section 21 Notification PDF (unsigned) - Override mixin"""
        self.ensure_one()
        return self.env.ref('bhuarjan.action_report_section21_notification').report_action(self)
    
    def action_generate_pdf(self):
        """Generate Section 21 Notification PDF - Legacy method"""
        return self.action_download_unsigned_file()
    
    def action_mark_signed(self):
        """Mark notification as signed"""
        self.ensure_one()
        if not self.signed_document_file:
            raise ValidationError(_('Please upload signed document first.'))
        self.state = 'signed'
        if not self.signed_date:
            self.signed_date = fields.Date.today()


class Section21LandParcel(models.Model):
    _name = 'bhu.section21.land.parcel'
    _description = 'Section 21 Land Parcel'
    _order = 'khasra_number'

    notification_id = fields.Many2one('bhu.section21.notification', string='Notification', required=True, ondelete='cascade')
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर', required=True)
    area_hectares = fields.Float(string='Area (Hectares) / अर्जित रकबा (हेक्टेयर में)', required=True, digits=(16, 4))
    remark = fields.Char(string='Remark / रिमार्क', help='Additional remarks for this land parcel')

