# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Payment(models.Model):
    _name = 'tende_ai.payment'
    _description = 'Payment Record'
    _order = 'transaction_date desc'

    bidder_id = fields.Many2one('tende_ai.bidder', string='Bidder', required=True, ondelete='cascade', readonly=True)
    job_id = fields.Many2one(
        'tende_ai.job',
        string='Job',
        related='bidder_id.job_id',
        readonly=True,
        store=True,
        index=True,
    )
    
    # Related fields for easier display
    company_name = fields.Char(string='Company Name', related='bidder_id.vendor_company_name', readonly=True, store=True)
    
    vendor = fields.Char(string='Vendor', tracking=True)
    payment_mode = fields.Char(string='Payment Mode', tracking=True)
    bank_name = fields.Char(string='Bank Name', tracking=True)
    transaction_id = fields.Char(string='Transaction ID', tracking=True, index=True)
    amount_inr = fields.Char(string='Amount (INR)', tracking=True)
    transaction_date = fields.Char(string='Transaction Date', tracking=True)
    status = fields.Char(string='Status', tracking=True)

