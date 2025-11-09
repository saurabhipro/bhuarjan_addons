# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaymentReconciliationBank(models.Model):
    _name = 'bhu.payment.reconciliation.bank'
    _description = 'Payment Reconciliation (Bank File) / भुगतान समाधान (बैंक फ़ाइल)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reconciliation_date desc, name'

    name = fields.Char(string='Reconciliation Number / समाधान संख्या', required=True, default='New', tracking=True)
    reconciliation_date = fields.Date(string='Reconciliation Date / समाधान दिनांक', required=True, 
                                     default=fields.Date.today, tracking=True)
    
    # Related Records
    payment_file_id = fields.Many2one('bhu.payment.file', string='Payment File / भुगतान फ़ाइल', required=True, tracking=True)
    village_id = fields.Many2one('bhu.village', string='Village / ग्राम', related='payment_file_id.village_id', store=True, readonly=True)
    project_id = fields.Many2one('bhu.project', string='Project / परियोजना', related='payment_file_id.project_id', store=True, readonly=True)
    
    # Bank File Upload
    bank_file = fields.Binary(string='Bank File / बैंक फ़ाइल', required=True, tracking=True)
    bank_file_filename = fields.Char(string='Bank File Name / बैंक फ़ाइल नाम')
    upload_date = fields.Date(string='Upload Date / अपलोड दिनांक', default=fields.Date.today, tracking=True)
    
    # Reconciliation Lines
    reconciliation_line_ids = fields.One2many('bhu.payment.reconciliation.bank.line', 'reconciliation_id', 
                                             string='Reconciliation Lines / समाधान पंक्तियां')
    
    # Summary
    total_payments = fields.Integer(string='Total Payments / कुल भुगतान', compute='_compute_summary', store=True)
    settled_count = fields.Integer(string='Settled / निपटाया गया', compute='_compute_summary', store=True)
    failed_count = fields.Integer(string='Failed / असफल', compute='_compute_summary', store=True)
    pending_count = fields.Integer(string='Pending / लंबित', compute='_compute_summary', store=True)
    total_amount = fields.Float(string='Total Amount / कुल राशि', compute='_compute_summary', store=True, digits=(16, 2))
    settled_amount = fields.Float(string='Settled Amount / निपटाई गई राशि', compute='_compute_summary', store=True, digits=(16, 2))
    failed_amount = fields.Float(string='Failed Amount / असफल राशि', compute='_compute_summary', store=True, digits=(16, 2))
    
    state = fields.Selection([
        ('draft', 'Draft / प्रारूप'),
        ('processed', 'Processed / प्रसंस्कृत'),
        ('completed', 'Completed / पूर्ण'),
    ], string='Status / स्थिति', default='draft', tracking=True)
    
    @api.depends('reconciliation_line_ids', 'reconciliation_line_ids.status', 'reconciliation_line_ids.credit_amount')
    def _compute_summary(self):
        """Compute reconciliation summary"""
        for record in self:
            lines = record.reconciliation_line_ids
            record.total_payments = len(lines)
            record.settled_count = len(lines.filtered(lambda l: l.status == 'settled'))
            record.failed_count = len(lines.filtered(lambda l: l.status == 'failed'))
            record.pending_count = len(lines.filtered(lambda l: l.status == 'pending'))
            record.total_amount = sum(lines.mapped('credit_amount'))
            record.settled_amount = sum(lines.filtered(lambda l: l.status == 'settled').mapped('credit_amount'))
            record.failed_amount = sum(lines.filtered(lambda l: l.status == 'failed').mapped('credit_amount'))
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate reconciliation number if not provided"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bhu.payment.reconciliation.bank') or 'New'
        return super().create(vals_list)
    
    def action_process_bank_file(self):
        """Process uploaded bank file and match with payment lines"""
        self.ensure_one()
        if not self.bank_file:
            raise ValidationError(_('Please upload bank file first.'))
        
        # Decode bank file
        import base64
        import csv
        import io
        
        try:
            file_content = base64.b64decode(self.bank_file)
            # Try to decode as text
            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8')
            
            # Parse CSV/TXT file
            reader = csv.DictReader(io.StringIO(file_content))
            
            # Clear existing lines
            self.reconciliation_line_ids = [(5, 0, 0)]
            
            # Create reconciliation lines from bank file
            line_vals = []
            for row in reader:
                # Map bank file columns to reconciliation line fields
                line_vals.append((0, 0, {
                    'utr_number': row.get('UTR Number', '') or row.get('UTR', ''),
                    'transaction_reference': row.get('Transaction Reference', '') or row.get('Transaction Ref', ''),
                    'beneficiary_account': row.get('Beneficiary Account', '') or row.get('Account Number', ''),
                    'beneficiary_name': row.get('Beneficiary Name', ''),
                    'beneficiary_bank_code': row.get('Beneficiary Bank Code', '') or row.get('IFSC Code', ''),
                    'credit_amount': float(row.get('Credit Amount', 0) or 0),
                    'status': row.get('Status', '').lower() if row.get('Status') else 'pending',
                    'error': row.get('Error', ''),
                    'payment_id': row.get('Payment Id', ''),
                }))
            
            if line_vals:
                self.reconciliation_line_ids = line_vals
                self.state = 'processed'
                
                # Match with payment file lines
                self._match_payments()
        except Exception as e:
            raise ValidationError(_('Error processing bank file: %s') % str(e))
    
    def _match_payments(self):
        """Match bank file transactions with payment file lines"""
        self.ensure_one()
        if not self.payment_file_id:
            return
        
        # Get payment file lines
        payment_lines = self.payment_file_id.payment_line_ids
        
        # Match reconciliation lines with payment lines
        for recon_line in self.reconciliation_line_ids:
            # Try to match by account number and amount
            matched_payment = payment_lines.filtered(
                lambda p: p.account_number == recon_line.beneficiary_account and
                         abs(p.net_payable_amount - recon_line.credit_amount) < 0.01
            )
            
            if matched_payment:
                recon_line.payment_line_id = matched_payment[0].id
                # Determine status based on bank file status
                bank_status = (recon_line.status or '').lower()
                if bank_status == 'executed' or bank_status == 'settled':
                    recon_line.status = 'settled'
                elif recon_line.error or bank_status == 'failed':
                    recon_line.status = 'failed'
                else:
                    recon_line.status = 'pending'
            else:
                recon_line.status = 'pending'


class PaymentReconciliationBankLine(models.Model):
    _name = 'bhu.payment.reconciliation.bank.line'
    _description = 'Payment Reconciliation Bank Line / भुगतान समाधान बैंक पंक्ति'
    _order = 'utr_number'

    reconciliation_id = fields.Many2one('bhu.payment.reconciliation.bank', string='Reconciliation', 
                                        required=True, ondelete='cascade')
    
    # Bank File Data
    utr_number = fields.Char(string='UTR Number / यूटीआर संख्या')
    transaction_reference = fields.Char(string='Transaction Reference / लेनदेन संदर्भ')
    beneficiary_account = fields.Char(string='Beneficiary Account / लाभार्थी खाता')
    beneficiary_name = fields.Char(string='Beneficiary Name / लाभार्थी नाम')
    beneficiary_bank_code = fields.Char(string='Beneficiary Bank Code / लाभार्थी बैंक कोड')
    credit_amount = fields.Float(string='Credit Amount / क्रेडिट राशि', digits=(16, 2))
    status = fields.Selection([
        ('pending', 'Pending / लंबित'),
        ('settled', 'Settled / निपटाया गया'),
        ('failed', 'Failed / असफल'),
    ], string='Status / स्थिति', default='pending', tracking=True)
    error = fields.Text(string='Error / त्रुटि')
    payment_id = fields.Char(string='Payment ID / भुगतान आईडी')
    
    # Matched Payment Line
    payment_line_id = fields.Many2one('bhu.payment.file.line', string='Matched Payment Line / मिलान भुगतान पंक्ति')
    
    # Computed fields from matched payment
    expected_amount = fields.Float(string='Expected Amount / अपेक्षित राशि', 
                                  related='payment_line_id.net_payable_amount', readonly=True, digits=(16, 2))
    amount_difference = fields.Float(string='Amount Difference / राशि अंतर', 
                                    compute='_compute_amount_difference', store=True, digits=(16, 2))
    
    @api.depends('credit_amount', 'expected_amount')
    def _compute_amount_difference(self):
        """Compute difference between expected and actual amount"""
        for record in self:
            if record.expected_amount and record.credit_amount:
                record.amount_difference = record.credit_amount - record.expected_amount
            else:
                record.amount_difference = 0.0

