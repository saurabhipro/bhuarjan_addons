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
    
    # Case Details
    case_number = fields.Char(string='Case Number / भू.अर्जन प्र. क्र.', related='award_id.case_number', readonly=True)
    patwari_halka_number = fields.Char(string='Patwari Halka Number / प.ह.नं.', related='award_id.patwari_halka_number', readonly=True)
    award_date = fields.Date(string='Award Date / अवार्ड दिनांक', related='award_id.award_date', readonly=True)
    
    # District, Tehsil
    district_id = fields.Many2one('bhu.district', string='District / जिला', related='village_id.district_id', store=True, readonly=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil / तहसील', related='village_id.tehsil_id', store=True, readonly=True)
    
    # Payment Lines
    payment_line_ids = fields.One2many('bhu.payment.file.line', 'payment_file_id', string='Payment Lines / भुगतान पंक्तियां')
    
    # Totals
    total_compensation = fields.Float(string='Total Compensation / कुल मुआवजा', compute='_compute_totals', store=True, digits=(16, 2))
    total_tds = fields.Float(string='Total TDS / कुल टीडीएस', compute='_compute_totals', store=True, digits=(16, 2))
    total_net_payable = fields.Float(string='Total Net Payable / कुल शुद्ध देय', compute='_compute_totals', store=True, digits=(16, 2))
    total_net_payable_text = fields.Char(string='Total Net Payable (Text) / कुल शुद्ध देय (पाठ)')
    
    # File Generation
    generated_file = fields.Binary(string='Generated File / जेनरेट की गई फ़ाइल')
    generated_file_filename = fields.Char(string='File Name / फ़ाइल नाम')
    generation_date = fields.Date(string='Generation Date / जेनरेशन दिनांक', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('generated', 'Generated / जेनरेट किया गया'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('payment_line_ids.compensation_amount', 'payment_line_ids.tds_deduction', 'payment_line_ids.net_payable_amount')
    def _compute_totals(self):
        """Compute totals from payment lines"""
        for record in self:
            record.total_compensation = sum(record.payment_line_ids.mapped('compensation_amount'))
            record.total_tds = sum(record.payment_line_ids.mapped('tds_deduction'))
            record.total_net_payable = sum(record.payment_line_ids.mapped('net_payable_amount'))
    
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
                'landowner_id': landowner.id,
                'bank_name': landowner.bank_name or '',
                'bank_branch': landowner.bank_branch or '',
                'account_number': landowner.account_number or '',
                'ifsc_code': landowner.ifsc_code or '',
                'compensation_amount': comp_line.payable_compensation_amount,
                'tds_deduction': 0.0,  # Default, can be updated
                'net_payable_amount': comp_line.payable_compensation_amount,
            }))
            serial += 1
        
        if line_vals:
            self.payment_line_ids = line_vals
    
    def action_generate_file(self):
        """Generate payment file (Excel/Annexure)"""
        self.ensure_one()
        if not self.payment_line_ids:
            raise ValidationError(_('Please populate payment lines first. Select Award and Village, then save the record.'))
        
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
        """Generate Excel file based on template"""
        self.ensure_one()
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Annexure')
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        border_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        # Row 1: Title "Annexure" in column K
        worksheet.write(0, 10, 'Annexure', title_format)
        
        # Row 2: Case Number
        case_num_text = f"राजस्व प्रकरण क्रमांक {self.case_number or '........................'} / अ-82 वर्ष {self.award_date.strftime('%Y-%m') if self.award_date else '2018-19'}"
        worksheet.write(1, 6, case_num_text, cell_format)
        
        # Row 3: Village, Tehsil, District
        village_text = f"ग्राम {self.village_id.name or '........................'}"
        tehsil_dist_text = f"तहसील {self.tehsil_id.name or '........................'} व जिला {self.district_id.name or '........................'} (छ.ग.)"
        worksheet.write(2, 6, village_text, cell_format)
        worksheet.write(2, 8, tehsil_dist_text, cell_format)
        
        # Row 4: Instruction
        instruction1 = "प्रकरण सक्षम प्रस्तुत ।"
        worksheet.write(3, 0, instruction1, cell_format)
        
        # Row 5: Detailed instruction
        award_date_str = self.award_date.strftime('%d.%m.%Y') if self.award_date else '26.12.2019'
        instruction2 = f"प्रकरण में पारित आवार्ड दिनांक {award_date_str} के अनुसार निम्नलिखित पक्षकारों / प्रभावित भूस्वामियों को मुआवजा का भुगतान हेतु निम्नानुसार सूची तैयार कर संबंधित भू-स्वामी के बैंक खाते में उनकी मुआवजा राशि RTGS के माध्यम से जमा करावे ।"
        worksheet.merge_range(4, 0, 4, 10, instruction2, cell_format)
        
        # Row 6: Sub-headers
        worksheet.write(5, 0, 'ग्राम', header_format)
        worksheet.write(5, 4, f"तहसील {self.tehsil_id.name or '........................'} व जिला {self.district_id.name or '........................'} (छ.ग.)", header_format)
        
        # Row 7: Column headers
        headers = [
            'स.क.',  # Serial No
            'अवॉर्ड स. क.',  # Award Serial No
            'पक्षकार का नाम एवं पिता/पति का नाम',  # Name
            'बैंक का नाम',  # Bank Name
            'शाखा',  # Branch
            'खाता क्रमांक',  # Account Number
            'आईएफएस कोड',  # IFSC Code
            'मुआवजा राशि',  # Compensation Amount
            'टीडीएस कटौती यदि हो तो',  # TDS Deduction
            'शुद्ध भुगतान की राशि',  # Net Payable Amount
            'रिमार्क'  # Remark
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, border_format)
        
        # Data rows (starting from row 8, index 7)
        row = 7
        for line in self.payment_line_ids:
            # Serial Number
            worksheet.write(row, 0, line.serial_number, border_format)
            # Award Serial Number
            worksheet.write(row, 1, line.award_serial_number, border_format)
            # Name with Father/Husband name
            name_text = f"{line.landowner_name or ''}"
            if line.father_husband_name:
                name_text += f" व. {line.father_husband_name}"
            worksheet.write(row, 2, name_text, border_format)
            # Bank Name
            worksheet.write(row, 3, line.bank_name or '', border_format)
            # Branch
            worksheet.write(row, 4, line.bank_branch or '', border_format)
            # Account Number
            worksheet.write(row, 5, line.account_number or '', border_format)
            # IFSC Code
            worksheet.write(row, 6, line.ifsc_code or '', border_format)
            # Compensation Amount
            worksheet.write(row, 7, line.compensation_amount, number_format)
            # TDS Deduction
            worksheet.write(row, 8, line.tds_deduction, number_format)
            # Net Payable Amount
            worksheet.write(row, 9, line.net_payable_amount, number_format)
            # Remark
            worksheet.write(row, 10, line.remark or '', border_format)
            row += 1
        
        # Total row (data starts at row 8, which is index 7)
        total_row = row
        first_data_row = 8  # Excel row number (1-indexed)
        last_data_row = row  # Excel row number (1-indexed)
        worksheet.write(total_row, 2, 'योग -', header_format)
        worksheet.write_formula(total_row, 7, f'=SUM(H{first_data_row}:H{last_data_row})', number_format)  # Total Compensation
        worksheet.write_formula(total_row, 8, f'=SUM(I{first_data_row}:I{last_data_row})', number_format)  # Total TDS
        worksheet.write_formula(total_row, 9, f'=SUM(J{first_data_row}:J{last_data_row})', number_format)  # Total Net Payable
        
        # Footer: Amount in words
        footer_row = total_row + 1
        worksheet.write(footer_row, 0, 'अक्षरी:-', cell_format)
        worksheet.write(footer_row, 1, self.total_net_payable_text or '', cell_format)
        
        # Footer: Instructions
        footer_row += 1
        instruction_text = f"उक्त सारणी के कालम 10 में अंकित धनराशि की कुल {self.total_net_payable:.2f} रू. का चेक संख्या .................................... दिनांक .................................... हस्ताक्षर कर प्रेषित । संबंधित भू-स्वामी के बैंक खाते में उनकी मुआवजा राशि को RTGS के माध्यम से जमा करावे एवं जमा की राशि की जानकारी इस कार्यालय को भी भेजे ।"
        worksheet.merge_range(footer_row, 0, footer_row, 10, instruction_text, cell_format)
        
        # Signatory section
        signatory_row = footer_row + 2
        worksheet.write(signatory_row, 6, 'सक्षम प्राधिकारी भू-अर्जन एवं', cell_format)
        worksheet.write(signatory_row + 1, 6, f'अनुविभागीय अधिकारी (रा.) {self.tehsil_id.name or "कोरबा"},', cell_format)
        worksheet.write(signatory_row + 2, 6, f'जिला {self.district_id.name or "कोरबा"} (छ.ग.)', cell_format)
        
        # Set column widths
        worksheet.set_column('A:A', 8)   # Serial No
        worksheet.set_column('B:B', 12)  # Award Serial No
        worksheet.set_column('C:C', 35)  # Name
        worksheet.set_column('D:D', 20)  # Bank Name
        worksheet.set_column('E:E', 15)  # Branch
        worksheet.set_column('F:F', 18)  # Account Number
        worksheet.set_column('G:G', 15)  # IFSC Code
        worksheet.set_column('H:H', 18)  # Compensation Amount
        worksheet.set_column('I:I', 18)  # TDS Deduction
        worksheet.set_column('J:J', 20)  # Net Payable Amount
        worksheet.set_column('K:K', 20)  # Remark
        
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
    tds_deduction = fields.Float(string='TDS Deduction / टीडीएस कटौती', digits=(16, 2), default=0.0)
    net_payable_amount = fields.Float(string='Net Payable Amount / शुद्ध भुगतान की राशि', 
                                      compute='_compute_net_payable', store=True, digits=(16, 2))
    
    # Remarks
    remark = fields.Text(string='Remark / रिमार्क')
    
    @api.depends('compensation_amount', 'tds_deduction')
    def _compute_net_payable(self):
        """Compute net payable amount"""
        for record in self:
            record.net_payable_amount = record.compensation_amount - record.tds_deduction

