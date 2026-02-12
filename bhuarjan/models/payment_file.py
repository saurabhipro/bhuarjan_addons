# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False
    _logger.warning("xlsxwriter library not found. Excel export will not be available.")


class PaymentFile(models.Model):
    _name = 'bhu.payment.file'
    _description = 'Payment File / भुगतान फ़ाइल'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Payment File Number / भुगतान फ़ाइल संख्या', required=True, default='New', tracking=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', required=True, tracking=True, ondelete='cascade')
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', required=True, tracking=True)
    award_id = fields.Many2one('bhu.draft.award', string='Draft Award / अवार्ड', required=True, tracking=True)
    
    # Case Details - removed as fields no longer exist in award model
    
    # District, Tehsil
    district_id = fields.Many2one('bhu.district', string='District / जिला', related='village_id.district_id', store=True, readonly=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', related='village_id.tehsil_id', store=True, readonly=True)
    department_id = fields.Many2one('bhu.department', string='Department / विभाग', related='project_id.department_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.INR'))
    
    debit_account_number = fields.Char(string='Debit Account Number / डेबिट खाता संख्या', tracking=True)
    
    _sql_constraints = [
        ('unique_project_village_payment', 'unique(project_id, village_id)', 
         'A payment file already exists for this village and project!')
    ]
    
    # Payment Lines
    payment_line_ids = fields.One2many('bhu.payment.file.line', 'payment_file_id', string='Payment Lines / भुगतान पंक्तियां')
    
    # Totals
    total_compensation = fields.Float(string='Total Compensation / कुल मुआवजा', compute='_compute_totals', store=True, digits=(16, 2))
    total_net_payable = fields.Float(string='Total Net Payable / कुल शुद्ध देय', compute='_compute_totals', store=True, digits=(16, 2))
    total_net_payable_text = fields.Char(string='Total Net Payable (Text) / कुल शुद्ध देय (पाठ)', compute='_compute_totals', store=True)
    
    # File Generation
    generated_file = fields.Binary(string='Generated File / जेनरेट की गई फ़ाइल')
    generated_file_filename = fields.Char(string='File Name / फ़ाइल नाम')
    generation_date = fields.Date(string='Generation Date / जेनरेशन दिनांक', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    def amount_to_text(self, amount):
        """Convert amount to text (Indian system)"""
        from odoo.tools import amount_to_text_en
        # Odoo's default is English, but we can use it as a base
        # For Hindi, we might need a custom tool, but for now let's use standard or just keep it char
        try:
            return self.currency_id.amount_to_text(amount)
        except:
            return str(amount)
    
    @api.depends('payment_line_ids.compensation_amount', 'payment_line_ids.net_payable_amount')
    def _compute_totals(self):
        """Compute totals from payment lines"""
        for record in self:
            record.total_compensation = sum(record.payment_line_ids.mapped('compensation_amount'))
            record.total_net_payable = sum(record.payment_line_ids.mapped('net_payable_amount'))
            record.total_net_payable_text = record.amount_to_text(record.total_net_payable)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate payment file number if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                # Try to use sequence settings from settings master
                project_id = vals.get('project_id')
                village_id = vals.get('village_id')
                if project_id:
                    sequence_number = self.env['bhuarjan.settings.master'].get_sequence_number(
                        'payment_file', project_id, village_id=village_id
                    )
                    if sequence_number:
                        vals['name'] = sequence_number
                    else:
                        # Fallback to ir.sequence
                        vals['name'] = self.env['ir.sequence'].next_by_code('bhu.payment.file') or 'New'
                else:
                    # No project_id, use fallback
                    vals['name'] = self.env['ir.sequence'].next_by_code('bhu.payment.file') or 'New'
        records = super().create(vals_list)
        # Auto-populate payment lines from award compensation lines
        for record in records:
            # Set default debit account from settings
            if not record.debit_account_number:
                settings = self.env['bhuarjan.settings.master'].get_settings_master()
                record.debit_account_number = settings.debit_account_number
            
            if record.award_id and record.village_id:
                record._populate_payment_lines()
        return records
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Reset village and award when project changes"""
        self.village_id = False
        self.award_id = False
        if self.project_id:
            return {'domain': {'village_id': [('id', 'in', self.project_id.village_ids.ids)]}}
        return {'domain': {'village_id': []}}
    
    @api.onchange('village_id')
    def _onchange_village_id(self):
        """Reset award when village changes and filter awards"""
        self.award_id = False
        if self.village_id and self.project_id:
            awards = self.env['bhu.draft.award'].search([
                ('project_id', '=', self.project_id.id),
                ('village_id', '=', self.village_id.id)
            ])
            if len(awards) == 1:
                self.award_id = awards[0].id
            return {'domain': {'award_id': [('id', 'in', awards.ids)]}}
        return {'domain': {'award_id': []}}
    
    @api.onchange('award_id', 'village_id')
    def _onchange_award_village(self):
        """Auto-populate payment lines when award or village changes"""
        if self.award_id and self.village_id:
            self._populate_payment_lines()
    
    def _populate_payment_lines(self):
        """Populate payment lines from award compensation lines"""
        self.ensure_one()
        if not self.award_id or not self.village_id:
            return
        
        # Get compensation lines for this village
        compensation_lines = self.award_id.compensation_line_ids.filtered(
            lambda l: l.landowner_id.village_id.id == self.village_id.id
        )
        
        # Clear existing lines
        self.payment_line_ids = [(5, 0, 0)]
        
        # Create payment lines
        line_vals = []
        serial = 1
        for comp_line in compensation_lines:
            landowner = comp_line.landowner_id
            line_vals.append((0, 0, {
                'serial_number': serial,
                'award_serial_number': comp_line.serial_number,
                'khasra_number': comp_line.khasra_number or '',
                'landowner_id': landowner.id,
                'bank_name': landowner.bank_name or '',
                'bank_branch': landowner.bank_branch or '',
                'account_number': landowner.account_number or '',
                'ifsc_code': landowner.ifsc_code or '',
                'compensation_amount': comp_line.payable_compensation_amount,
                'net_payable_amount': comp_line.payable_compensation_amount,
            }))
            serial += 1
        
        if line_vals:
            self.payment_line_ids = line_vals
    
    def action_generate_file(self):
        """Generate payment file (Excel/Annexure)"""
        self.ensure_one()
        if not self.payment_line_ids:
            self._populate_payment_lines()
            
        if not self.payment_line_ids:
            raise ValidationError(_('No compensation data found for this village and project in the selected Award.'))
        
        if not HAS_XLSXWRITER:
            raise ValidationError(_('xlsxwriter library is required for Excel export. Please install it: pip install xlsxwriter'))
        
        # Generate Excel file
        excel_file = self._generate_excel_file()
        
        # Save to record
        filename = f'Payment_File_{self.name}_{self.village_id.name or "Unknown"}.xlsx'
        self.write({
            'generated_file': base64.b64encode(excel_file),
            'generated_file_filename': filename,
            'state': 'generated',
            'generation_date': fields.Date.today()
        })
        
        # Create attachment for download
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_file),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'bhu.payment.file',
            'res_id': self.id,
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def _generate_excel_file(self):
        """Generate Excel file based on Template 1 (Bank Export)"""
        self.ensure_one()
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('PaymentData')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        # Template 1 Headers
        headers = [
            'Bulk Transaction Type',
            'External Ref No',
            'Debit Account number',
            'Amount',
            'Beneficiary Name',
            'Beneficiary Bank Name',
            'Beneficiary Account Number',
            'IFSC',
            'Purpose 1',
            'Purpose 2',
            'Cheque Number',
            'Project',
            'Village',
            'Khasra'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        row = 1
        for line in self.payment_line_ids:
            worksheet.write(row, 0, 'N', cell_format)  # Bulk Transaction Type
            worksheet.write(row, 1, self.name, cell_format)  # External Ref No
            worksheet.write(row, 2, self.debit_account_number or '', cell_format)  # Debit Account number
            worksheet.write(row, 3, line.net_payable_amount, cell_format)  # Amount
            worksheet.write(row, 4, line.landowner_name or '', cell_format)  # Beneficiary Name
            worksheet.write(row, 5, line.bank_name or '', cell_format)  # Beneficiary Bank Name
            worksheet.write(row, 6, line.account_number or '', cell_format)  # Beneficiary Account Number
            worksheet.write(row, 7, line.ifsc_code or '', cell_format)  # IFSC
            worksheet.write(row, 8, self.village_id.name or '', cell_format)  # Purpose 1
            worksheet.write(row, 9, self.project_id.name or '', cell_format)  # Purpose 2
            worksheet.write(row, 10, '', cell_format)  # Cheque Number
            worksheet.write(row, 11, self.project_id.name or '', cell_format)  # Project
            worksheet.write(row, 12, self.village_id.name or '', cell_format)  # Village
            worksheet.write(row, 13, line.khasra_number or '', cell_format)  # Khasra
            row += 1
        
        # Set column widths
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 25)
        worksheet.set_column('G:G', 25)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 15)
        worksheet.set_column('L:N', 25)
        
        workbook.close()
        output.seek(0)
        return output.read()


class PaymentFileLine(models.Model):
    _name = 'bhu.payment.file.line'
    _description = 'Payment File Line / भुगतान फ़ाइल पंक्ति'
    _order = 'serial_number'

    payment_file_id = fields.Many2one('bhu.payment.file', string='Payment File', required=True, ondelete='cascade')
    
    # Serial Numbers
    serial_number = fields.Integer(string='Serial Number / स.क.', required=True, default=1)
    award_serial_number = fields.Integer(string='Award Serial Number / अवॉर्ड स.क.', required=True)
    khasra_number = fields.Char(string='Khasra Number / खसरा नंबर')
    
    # Landowner Details
    landowner_id = fields.Many2one('bhu.landowner', string='Landowner / भूमिस्वामी', required=False, ondelete='set null')
    landowner_name = fields.Char(string='Landowner Name / पक्षकार का नाम', related='landowner_id.name', store=True, readonly=True)
    father_husband_name = fields.Char(string='Father/Husband Name / पिता/पति का नाम', 
                                     related='landowner_id.father_name', store=True, readonly=True)
    
    # Bank Details
    bank_name = fields.Char(string='Bank Name / बैंक का नाम', required=True)
    bank_branch = fields.Char(string='Branch / शाखा', required=True)
    account_number = fields.Char(string='Account Number / खाता क्रमांक', required=True)
    ifsc_code = fields.Char(string='IFSC Code / आईएफएससी कोड', required=True)
    
    # Payment Amounts
    compensation_amount = fields.Float(string='Compensation Amount / मुआवजा राशि', required=True, digits=(16, 2))
    net_payable_amount = fields.Float(string='Net Payable Amount / शुद्ध भुगतान की राशि', 
                                      compute='_compute_net_payable', store=True, digits=(16, 2))
    
    currency_id = fields.Many2one('res.currency', string='Currency', related='payment_file_id.currency_id')
    
    # Remarks
    remark = fields.Text(string='Remark / रिमार्क')
    
    @api.depends('compensation_amount')
    def _compute_net_payable(self):
        """Compute net payable amount"""
        for record in self:
            record.net_payable_amount = record.compensation_amount

