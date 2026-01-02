# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Tender(models.Model):
    _name = 'tende_ai.tender'
    _description = 'Tender Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    job_id = fields.Many2one('tende_ai.job', string='Job', required=True, ondelete='cascade', readonly=True)
    
    # Basic Information
    department_name = fields.Char(string='Department Name', tracking=True)
    tender_id = fields.Char(string='Tender ID', tracking=True, index=True)
    ref_no = fields.Char(string='Reference Number', tracking=True, index=True)
    tender_creator = fields.Char(string='Tender Creator', tracking=True)
    
    # Classification
    procurement_category = fields.Char(string='Procurement Category', tracking=True)
    tender_type = fields.Char(string='Tender Type', tracking=True)
    organization_hierarchy = fields.Char(string='Organization Hierarchy', tracking=True)
    
    # Financial Information
    estimated_value_inr = fields.Char(string='Estimated Value (INR)', tracking=True)
    tender_currency = fields.Char(string='Tender Currency', tracking=True)
    bidding_currency = fields.Char(string='Bidding Currency', tracking=True)
    offer_validity_days = fields.Char(string='Offer Validity (Days)', tracking=True)
    
    # Reference Information
    previous_tender_no = fields.Char(string='Previous Tender Number', tracking=True)
    
    # Dates
    published_on = fields.Char(string='Published On', tracking=True)
    bid_submission_start = fields.Char(string='Bid Submission Start', tracking=True)
    bid_submission_end = fields.Char(string='Bid Submission End', tracking=True)
    tender_opened_on = fields.Char(string='Tender Opened On', tracking=True)
    
    # Description
    description = fields.Text(string='Description', tracking=True)
    nit = fields.Text(string='NIT', tracking=True)
    
    # Analytics
    analytics = fields.Text(string='Analytics (JSON)', readonly=True)
    
    # Related Records
    eligibility_criteria = fields.One2many('tende_ai.eligibility_criteria', 'tender_id', string='Eligibility Criteria')

