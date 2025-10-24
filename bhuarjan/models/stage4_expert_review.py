# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _


class Stage4ExpertReview(models.Model):
    _name = 'bhu.stage4.expert.review'
    _description = 'Stage 4: Expert Group Review (Section 7)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Basic Information
    review_date = fields.Date(string='Review Date', required=True, tracking=True)
    review_purpose = fields.Text(string='Review Purpose', required=True)
    
    # Location Information
    district_id = fields.Many2one('bhu.district', string='District', required=True)
    tehsil_id = fields.Many2one('bhu.tehsil', string='Tehsil', required=True)
    village_id = fields.Many2one('bhu.village', string='Village', required=True)
    
    # Expert Group Details
    expert_group_formed = fields.Boolean(string='Expert Group Formed', default=False)
    expert_group_date = fields.Date(string='Expert Group Formation Date')
    expert_group_chairman = fields.Char(string='Expert Group Chairman')
    expert_group_members = fields.Text(string='Expert Group Members')
    
    # Review Details
    review_scope = fields.Text(string='Review Scope', required=True)
    review_methodology = fields.Text(string='Review Methodology')
    review_findings = fields.Text(string='Review Findings')
    review_recommendations = fields.Text(string='Review Recommendations')
    
    # Technical Assessment
    technical_feasibility = fields.Selection([
        ('feasible', 'Feasible'),
        ('not_feasible', 'Not Feasible'),
        ('conditional', 'Conditional')
    ], string='Technical Feasibility')
    
    environmental_impact = fields.Selection([
        ('low', 'Low Impact'),
        ('medium', 'Medium Impact'),
        ('high', 'High Impact')
    ], string='Environmental Impact')
    
    social_impact = fields.Selection([
        ('low', 'Low Impact'),
        ('medium', 'Medium Impact'),
        ('high', 'High Impact')
    ], string='Social Impact')
    
    # Financial Assessment
    estimated_cost = fields.Monetary(string='Estimated Project Cost', currency_field='currency_id')
    cost_benefit_ratio = fields.Float(string='Cost-Benefit Ratio')
    economic_viability = fields.Selection([
        ('viable', 'Viable'),
        ('not_viable', 'Not Viable'),
        ('conditional', 'Conditional')
    ], string='Economic Viability')
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Review Documents
    review_report = fields.Binary(string='Review Report')
    review_report_filename = fields.Char(string='Review Report Filename')
    supporting_documents = fields.Binary(string='Supporting Documents')
    supporting_documents_filename = fields.Char(string='Supporting Documents Filename')
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_name = fields.Char(related='company_id.name', string='Company Name', store=True)
    
    # Related Records
    stage3_ids = fields.Many2many('bhu.stage3.jansunwai', string='Related Stage 3 Records')
    survey_ids = fields.Many2many('bhu.survey', string='Related Surveys')
    
    # Approval Details
    approval_date = fields.Date(string='Approval Date')
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
            vals['name'] = self.env['ir.sequence'].next_by_code('bhu.stage4.expert.review') or _('New')
        return super(Stage4ExpertReview, self).create(vals)

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
