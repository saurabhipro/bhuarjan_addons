# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Bidder(models.Model):
    _name = 'tende_ai.bidder'
    _description = 'Bidder/Company Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'vendor_company_name'

    job_id = fields.Many2one('tende_ai.job', string='Job', required=True, ondelete='cascade', readonly=True)
    
    # Company Information
    vendor_company_name = fields.Char(string='Company Name', required=True, tracking=True, index=True)
    company_address = fields.Text(string='Company Address', tracking=True)
    email_id = fields.Char(string='Email ID', tracking=True)
    contact_person = fields.Char(string='Contact Person', tracking=True)
    contact_no = fields.Char(string='Contact Number', tracking=True)
    
    # Registration Information
    pan = fields.Char(string='PAN', tracking=True)
    gstin = fields.Char(string='GSTIN', tracking=True)
    place_of_registration = fields.Char(string='Place of Registration', tracking=True)
    offer_validity_days = fields.Char(string='Offer Validity (Days)', tracking=True)
    
    # Related Records
    payments = fields.One2many('tende_ai.payment', 'bidder_id', string='Payments')
    work_experiences = fields.One2many('tende_ai.work_experience', 'bidder_id', string='Work Experiences')

