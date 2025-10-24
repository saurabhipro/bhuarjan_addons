# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _


class Stage5CollectorApproval(models.Model):
    _name = 'bhu.stage5.collector.approval'
    _description = 'Stage 5: Collector Approval (Section 8)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Basic Information
    application_date = fields.Date(string='Application Date', required=True, tracking=True)
    approval_purpose = fields.Text(string='Approval Purpose', required=True)
    
    # Location Information
    district_id = fields.Many2one('bhu.district', string='District', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    
    # Collector Details
    collector_name = fields.Char(string='Collector Name', required=True)
    collector_designation = fields.Char(string='Collector Designation', required=True)
    collector_office = fields.Char(string='Collector Office', required=True)
    
    # Application Details
    application_type = fields.Selection([
        ('land_acquisition', 'Land Acquisition'),
        ('rehabilitation', 'Rehabilitation'),
        ('resettlement', 'Resettlement'),
        ('compensation', 'Compensation')
    ], string='Application Type', required=True)
    
    application_summary = fields.Text(string='Application Summary', required=True)
    supporting_evidence = fields.Text(string='Supporting Evidence')
    
    # Review Process
    review_committee_formed = fields.Boolean(string='Review Committee Formed', default=False)
    review_committee_date = fields.Date(string='Review Committee Formation Date')
    review_committee_members = fields.Text(string='Review Committee Members')
    
    # Assessment Details
    land_requirement = fields.Float(string='Land Requirement (Acres)')
    affected_families = fields.Integer(string='Affected Families')
    estimated_compensation = fields.Monetary(string='Estimated Compensation', currency_field='currency_id')
    rehabilitation_package = fields.Text(string='Rehabilitation Package')
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Legal Compliance
    legal_compliance = fields.Selection([
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('conditional', 'Conditional')
    ], string='Legal Compliance')
    
    compliance_details = fields.Text(string='Compliance Details')
    legal_opinion = fields.Text(string='Legal Opinion')
    
    # Approval Process
    approval_authority = fields.Char(string='Approval Authority')
    approval_level = fields.Selection([
        ('collector', 'Collector Level'),
        ('commissioner', 'Commissioner Level'),
        ('secretary', 'Secretary Level'),
        ('minister', 'Minister Level')
    ], string='Approval Level')
    
    approval_conditions = fields.Text(string='Approval Conditions')
    approval_validity = fields.Date(string='Approval Validity')
    
    # Documents
    application_documents = fields.Binary(string='Application Documents')
    application_documents_filename = fields.Char(string='Application Documents Filename')
    approval_documents = fields.Binary(string='Approval Documents')
    approval_documents_filename = fields.Char(string='Approval Documents Filename')
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_name = fields.Char(related='company_id.name', string='Company Name', store=True)
    
    # Related Records
    stage4_ids = fields.Many2many('bhu.stage4.expert.review', string='Related Stage 4 Records')
    stage3_ids = fields.Many2many('bhu.stage3.jansunwai', string='Related Stage 3 Records')
    survey_ids = fields.Many2many('bhu.survey', string='Related Surveys')
    
    # Approval Details
    approval_date = fields.Date(string='Approval Date')
    approval_number = fields.Char(string='Approval Number')
    approved_by = fields.Char(string='Approved By')
    approval_remarks = fields.Text(string='Approval Remarks')
    
    # Signature Details
    signature_place = fields.Char(string='Signature Place')
    signature_date = fields.Date(string='Signature Date')
    signed_by = fields.Char(string='Signed By')
    designation = fields.Char(string='Designation')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('bhu.stage5.collector.approval') or _('New')
        return super(Stage5CollectorApproval, self).create(vals)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_start_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})
